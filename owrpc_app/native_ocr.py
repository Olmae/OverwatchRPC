"""Persistent Windows OCR bridge; images stay in memory, no external engine."""
import base64
import io
import json
import queue
import subprocess
import threading
from .detection import Word

SCRIPT = r'''
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Storage.Streams.InMemoryRandomAccessStream, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Storage.Streams.DataWriter, Windows.Foundation, ContentType=WindowsRuntime]
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]
function Await($operation, $type) {
    $task = $asTask.MakeGenericMethod($type).Invoke($null, @($operation))
    $task.GetAwaiter().GetResult()
}
$null = [Windows.Globalization.Language, Windows.Foundation, ContentType=WindowsRuntime]
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('en-US'))

while ($line = [Console]::ReadLine()) {
    $stream = $writer = $bitmap = $null
    try {
        if ($null -eq $engine) { throw 'No Windows OCR language installed. Install a language under Windows Settings.' }
        $bytes = [Convert]::FromBase64String($line)
        $stream = New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
        $writer = New-Object Windows.Storage.Streams.DataWriter($stream)
        $writer.WriteBytes($bytes)
        $null = Await ($writer.StoreAsync()) ([uint32])
        $stream.Seek(0)
        $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        $result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
        $words = @($result.Lines | ForEach-Object { $_.Words } | ForEach-Object {
            @{text=$_.Text; x=$_.BoundingRect.X; y=$_.BoundingRect.Y; width=$_.BoundingRect.Width; height=$_.BoundingRect.Height}
        })
        [Console]::WriteLine((ConvertTo-Json -Compress -Depth 4 -InputObject @{words=$words; width=$bitmap.PixelWidth; height=$bitmap.PixelHeight}))
    } catch {
        [Console]::WriteLine((ConvertTo-Json -Compress -InputObject @{error=$_.Exception.Message}))
    } finally {
        if ($bitmap) { $bitmap.Dispose() }
        if ($writer) { $null = $writer.DetachStream(); $writer.Dispose() }
        if ($stream) { $stream.Dispose() }
    }
}
'''


class WindowsOCR:
    def __init__(self):
        self.process = None
        self.lines = queue.Queue()
        self.language = "en-US"

    def start(self):
        script = SCRIPT.replace("'en-US'", repr(self.language))
        command = base64.b64encode(script.encode('utf-16le')).decode('ascii')
        self.process = subprocess.Popen(
            ['powershell.exe', '-NoLogo', '-NoProfile', '-NonInteractive', '-EncodedCommand', command],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding='utf-8', creationflags=(getattr(subprocess, 'CREATE_NO_WINDOW', 0) |
                           getattr(subprocess, 'BELOW_NORMAL_PRIORITY_CLASS', 0)))
        process, lines = self.process, self.lines

        def read():
            for line in process.stdout:
                lines.put(line)
            lines.put(None)
        threading.Thread(target=read, name='Windows OCR output', daemon=True).start()

    def configure(self, language):
        languages = {'eng': 'en-US', 'rus': 'ru-RU', 'deu': 'de-DE', 'fra': 'fr-FR',
                     'spa': 'es-ES', 'por': 'pt-BR', 'chi_sim': 'zh-Hans-CN',
                     'chi_tra': 'zh-Hant-TW', 'kor': 'ko-KR', 'jpn': 'ja-JP'}
        selected = languages.get(language.split('+')[0], language)
        if selected not in languages.values():
            raise ValueError('Unsupported Windows OCR language: ' + language)
        if self.language != selected:
            self.close()
            self.language = selected

    def words(self, image):
        if not self.process or self.process.poll() is not None:
            self.close()
            self.lines = queue.Queue()
            self.start()
        image = image.convert('RGB')
        # Keep glyph detail at Full HD; enforce the native engine's dimension cap.
        image.thumbnail((2500, 2500))
        stream = io.BytesIO()
        image.save(stream, format='PNG')
        try:
            self.process.stdin.write(base64.b64encode(stream.getvalue()).decode('ascii') + '\n')
            self.process.stdin.flush()
            line = self.lines.get(timeout=12)
            if line is None:
                raise RuntimeError('Windows OCR process stopped')
            data = json.loads(line)
            if 'error' in data:
                raise RuntimeError(data['error'])
            return [Word(w['text'], w['x']/data['width'], w['y']/data['height'],
                         w['width']/data['width'], w['height']/data['height']) for w in data['words']]
        except Exception:
            self.close()
            raise

    def close(self):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)
            for pipe in (self.process.stdin, self.process.stdout):
                if pipe:
                    pipe.close()
            self.process = None


_engine = WindowsOCR()

# Lazily started only when mixed-language name recognition is requested.
_latin_engine = WindowsOCR()
