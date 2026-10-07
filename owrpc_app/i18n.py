"""Offline UI translations; catalog identities never depend on the UI language."""

import locale
import sys

LANGUAGES = {
    'en': 'English', 'ru': 'Русский', 'zh-CN': '简体中文', 'pt-BR': 'Português (Brasil)',
    'es': 'Español', 'zh-TW': '繁體中文', 'ko': '한국어', 'fr': 'Français', 'de': 'Deutsch',
}


def normalize_language(value):
    value = (value or '').replace('_', '-').lower()
    if value.startswith('zh'):
        return 'zh-TW' if any(x in value for x in ('tw', 'hk', 'hant', 'mo')) else 'zh-CN'
    if value.startswith('pt'):
        return 'pt-BR'
    return next((code for code in LANGUAGES if value.split('-')[0] == code), 'en')


def system_language():
    if sys.platform == 'win32':
        import ctypes
        buffer = ctypes.create_unicode_buffer(85)
        if ctypes.windll.kernel32.GetUserDefaultLocaleName(buffer, len(buffer)):
            return normalize_language(buffer.value)
    try:
        return normalize_language(locale.getlocale()[0])
    except (ValueError, TypeError):
        return 'en'


def resolve_language(language):
    return system_language() if language == 'auto' else normalize_language(language)


# Rows follow LANGUAGES order after English. English text is also the fallback key.
_ROWS = {
    'Choosing a map': ('Выбор карты', '选择地图', 'Escolhendo o mapa', 'Eligiendo mapa', '選擇地圖', '전장 선택', 'Choix de la carte', 'Kartenauswahl'),
    'Activity': ('Активность', '活动', 'Atividade', 'Actividad', '活動', '활동', 'Activité', 'Aktivität'),
    'Settings': ('Настройки', '设置', 'Configurações', 'Ajustes', '設定', '설정', 'Paramètres', 'Einstellungen'),
    'Advanced': ('Расширенные', '高级', 'Avançado', 'Avanzado', '進階', '고급', 'Avancé', 'Erweitert'),
    'About': ('О приложении', '关于', 'Sobre', 'Acerca de', '關於', '정보', 'À propos', 'Über'),
    'Overwatch companion': ('Компаньон Overwatch', 'Overwatch 助手', 'Companheiro de Overwatch', 'Asistente de Overwatch', 'Overwatch 助手', '오버워치 도우미', 'Compagnon Overwatch', 'Overwatch-Begleiter'),
    'Pause': ('Пауза', '暂停', 'Pausar', 'Pausar', '暫停', '일시 정지', 'Pause', 'Pausieren'),
    'Resume': ('Продолжить', '继续', 'Retomar', 'Reanudar', '繼續', '재개', 'Reprendre', 'Fortsetzen'),
    'In menus': ('В меню', '在菜单中', 'Nos menus', 'En los menús', '在選單中', '메뉴', 'Dans les menus', 'Im Menü'),
    'In queue': ('Поиск матча', '排队中', 'Na fila', 'En cola', '排隊中', '대기열', 'En file', 'In der Warteschlange'),
    'In match': ('В матче', '对战中', 'Em partida', 'En partida', '對戰中', '경기 중', 'En partie', 'Im Match'),
    'In Menus': ('В меню', '在菜单中', 'Nos menus', 'En los menús', '在選單中', '메뉴', 'Dans les menus', 'Im Menü'),
    'In Queue': ('Поиск матча', '排队中', 'Na fila', 'En cola', '排隊中', '대기열', 'En file', 'In der Warteschlange'),
    'Waiting for a match': ('Ожидание матча', '等待对战', 'Aguardando partida', 'Esperando partida', '等待對戰', '경기 대기 중', 'En attente de partie', 'Warten auf ein Match'),
    'Playing {hero}': ('Играет за {hero}', '正在使用 {hero}', 'Jogando com {hero}', 'Jugando con {hero}', '正在使用 {hero}', '{hero} 플레이 중', 'Joue avec {hero}', 'Spielt {hero}'),
    'Map not selected': ('Карта не выбрана', '未选择地图', 'Mapa não selecionado', 'Mapa sin seleccionar', '未選擇地圖', '맵 미선택', 'Carte non sélectionnée', 'Keine Karte gewählt'),
    'Mode': ('Режим', '模式', 'Modo', 'Modo', '模式', '모드', 'Mode', 'Modus'),
    'Map': ('Карта', '地图', 'Mapa', 'Mapa', '地圖', '맵', 'Carte', 'Karte'),
    'Hero': ('Герой', '英雄', 'Herói', 'Héroe', '英雄', '영웅', 'Héros', 'Held'),
    'Choose a hero': ('Выбрать героя', '选择英雄', 'Escolher herói', 'Elegir héroe', '選擇英雄', '영웅 선택', 'Choisir un héros', 'Held wählen'),
    'Search heroes': ('Поиск героев', '搜索英雄', 'Buscar heróis', 'Buscar héroes', '搜尋英雄', '영웅 검색', 'Rechercher un héros', 'Helden suchen'),
    'Apply activity': ('Применить', '应用活动', 'Aplicar atividade', 'Aplicar actividad', '套用活動', '활동 적용', 'Appliquer', 'Aktivität anwenden'),
    'New match': ('Новый матч', '新对战', 'Nova partida', 'Nueva partida', '新對戰', '새 경기', 'Nouvelle partie', 'Neues Match'),
    'New match clears the hero and map and restarts the timer.': ('Новый матч сбрасывает героя, карту и таймер.', '新对战会清除英雄和地图并重置计时器。', 'Nova partida limpa herói e mapa e reinicia o tempo.', 'Nueva partida borra héroe y mapa y reinicia el tiempo.', '新對戰會清除英雄與地圖並重設計時器。', '새 경기는 영웅과 맵을 지우고 타이머를 초기화합니다.', 'Une nouvelle partie efface héros et carte et relance le chrono.', 'Ein neues Match setzt Held, Karte und Timer zurück.'),
    'Select your activity manually. Automatic recognition is optional in Advanced.': ('Выбери активность вручную. Автораспознавание доступно в расширенных настройках.', '手动选择活动。高级设置中可启用自动识别。', 'Selecione a atividade manualmente. Reconhecimento opcional em Avançado.', 'Selecciona la actividad manualmente. Reconocimiento opcional en Avanzado.', '手動選擇活動。進階設定可啟用自動辨識。', '활동을 직접 선택하세요. 자동 인식은 고급 설정에서 선택할 수 있습니다.', 'Choisissez votre activité. La reconnaissance est optionnelle dans Avancé.', 'Aktivität manuell wählen. Automatische Erkennung ist unter Erweitert optional.'),
    'Discord preview': ('Предпросмотр Discord', 'Discord 预览', 'Prévia do Discord', 'Vista previa de Discord', 'Discord 預覽', 'Discord 미리 보기', 'Aperçu Discord', 'Discord-Vorschau'),
    'Discord may arrange images and text differently.': ('Discord может иначе расположить изображения и текст.', 'Discord 的图片和文字布局可能不同。', 'O Discord pode organizar imagens e textos de outra forma.', 'Discord puede distribuir imágenes y texto de otra forma.', 'Discord 的圖片與文字排列可能不同。', 'Discord의 이미지와 텍스트 배치가 다를 수 있습니다.', 'Discord peut disposer images et texte différemment.', 'Discord kann Bilder und Text anders anordnen.'),
    'No map artwork': ('Нет изображения карты', '无地图图片', 'Sem imagem do mapa', 'Sin imagen del mapa', '無地圖圖片', '맵 이미지 없음', 'Aucune image de carte', 'Kein Kartenbild'),
    'No match timer': ('Таймер не запущен', '计时器未启动', 'Sem cronômetro', 'Sin cronómetro', '計時器未啟動', '타이머 없음', 'Aucun chrono', 'Kein Match-Timer'),
    'Match time · {time}': ('Время матча · {time}', '对战时间 · {time}', 'Tempo de partida · {time}', 'Tiempo de partida · {time}', '對戰時間 · {time}', '경기 시간 · {time}', 'Durée · {time}', 'Match-Zeit · {time}'),
    'Presence paused': ('Публикация приостановлена', '活动已暂停', 'Atividade pausada', 'Actividad pausada', '活動已暫停', '활동 일시 정지됨', 'Activité en pause', 'Aktivität pausiert'),
    'Connected to Discord': ('Подключено к Discord', '已连接 Discord', 'Conectado ao Discord', 'Conectado a Discord', '已連接 Discord', 'Discord 연결됨', 'Connecté à Discord', 'Mit Discord verbunden'),
    'Waiting for Discord…': ('Ожидание Discord…', '等待 Discord…', 'Aguardando Discord…', 'Esperando Discord…', '等待 Discord…', 'Discord 대기 중…', 'En attente de Discord…', 'Warten auf Discord…'),
    'Discord unavailable · retrying': ('Discord недоступен · повтор подключения', 'Discord 不可用 · 正在重试', 'Discord indisponível · tentando novamente', 'Discord no disponible · reintentando', 'Discord 無法使用 · 正在重試', 'Discord 연결 불가 · 재시도 중', 'Discord indisponible · nouvelle tentative', 'Discord nicht erreichbar · neuer Versuch'),
    'Presence hidden': ('Активность скрыта', '活动已隐藏', 'Atividade oculta', 'Actividad oculta', '活動已隱藏', '활동 숨김', 'Activité masquée', 'Aktivität ausgeblendet'),
    'Overwatch running': ('Overwatch запущен', 'Overwatch 正在运行', 'Overwatch em execução', 'Overwatch en ejecución', 'Overwatch 執行中', '오버워치 실행 중', 'Overwatch lancé', 'Overwatch läuft'),
    'Overwatch not running': ('Overwatch не запущен', 'Overwatch 未运行', 'Overwatch fechado', 'Overwatch no está abierto', 'Overwatch 未執行', '오버워치 실행 안 됨', 'Overwatch arrêté', 'Overwatch läuft nicht'),
    'Checking Overwatch…': ('Проверка Overwatch…', '正在检查 Overwatch…', 'Verificando Overwatch…', 'Comprobando Overwatch…', '正在檢查 Overwatch…', '오버워치 확인 중…', 'Vérification d’Overwatch…', 'Overwatch wird geprüft…'),
    'Start Discord desktop to publish your activity.': ('Открой настольный Discord для публикации активности.', '打开 Discord 桌面客户端以发布活动。', 'Abra o Discord para desktop para publicar sua atividade.', 'Abre Discord de escritorio para publicar tu actividad.', '開啟 Discord 桌面版以發布活動。', '활동을 게시하려면 Discord 데스크톱을 실행하세요.', 'Ouvrez Discord pour ordinateur pour publier votre activité.', 'Discord-Desktop öffnen, um die Aktivität zu veröffentlichen.'),
    'Activity is hidden until Overwatch starts.': ('Активность скрыта до запуска Overwatch.', 'Overwatch 启动前活动保持隐藏。', 'Atividade oculta até abrir Overwatch.', 'Actividad oculta hasta abrir Overwatch.', 'Overwatch 啟動前活動保持隱藏。', '오버워치 실행 전까지 활동이 숨겨집니다.', 'Activité masquée jusqu’au lancement d’Overwatch.', 'Aktivität bis zum Start von Overwatch ausgeblendet.'),
    'Your activity is being published.': ('Твоя активность публикуется.', '正在发布活动。', 'Sua atividade está sendo publicada.', 'Tu actividad se está publicando.', '正在發布活動。', '활동이 게시되고 있습니다.', 'Votre activité est publiée.', 'Deine Aktivität wird veröffentlicht.'),
    'Language': ('Язык', '语言', 'Idioma', 'Idioma', '語言', '언어', 'Langue', 'Sprache'),
    'System language': ('Язык системы', '系统语言', 'Idioma do sistema', 'Idioma del sistema', '系統語言', '시스템 언어', 'Langue du système', 'Systemsprache'),
    'General settings': ('Основные настройки', '常规设置', 'Configurações gerais', 'Ajustes generales', '一般設定', '일반 설정', 'Paramètres généraux', 'Allgemeine Einstellungen'),
    'Close window to tray': ('При закрытии сворачивать в трей', '关闭窗口时最小化到托盘', 'Fechar para a bandeja', 'Cerrar en la bandeja', '關閉視窗時縮小至系統匣', '닫으면 트레이로 최소화', 'Fermer dans la zone de notification', 'Beim Schließen in den Infobereich'),
    'Start hidden in tray': ('Запускать свёрнутым', '启动时隐藏到托盘', 'Iniciar na bandeja', 'Iniciar en la bandeja', '啟動時隱藏至系統匣', '트레이에서 시작', 'Démarrer masqué', 'Im Infobereich starten'),
    'Launch with Windows': ('Запускать вместе с Windows', '随 Windows 启动', 'Iniciar com o Windows', 'Iniciar con Windows', '隨 Windows 啟動', 'Windows 시작 시 실행', 'Lancer avec Windows', 'Mit Windows starten'),
    'Publish only while Overwatch runs': ('Показывать активность только при запущенном Overwatch', '仅在 Overwatch 运行时发布', 'Publicar só com Overwatch aberto', 'Publicar solo con Overwatch abierto', '僅在 Overwatch 執行時發布', '오버워치 실행 중에만 게시', 'Publier uniquement quand Overwatch est lancé', 'Nur bei laufendem Overwatch veröffentlichen'),
    'Show match timer': ('Показывать время матча', '显示对战时间', 'Mostrar tempo de partida', 'Mostrar tiempo de partida', '顯示對戰時間', '경기 시간 표시', 'Afficher la durée', 'Match-Zeit anzeigen'),
    'Save settings': ('Сохранить настройки', '保存设置', 'Salvar configurações', 'Guardar ajustes', '儲存設定', '설정 저장', 'Enregistrer', 'Einstellungen speichern'),
    'Settings saved': ('Настройки сохранены', '设置已保存', 'Configurações salvas', 'Ajustes guardados', '設定已儲存', '설정 저장됨', 'Paramètres enregistrés', 'Einstellungen gespeichert'),
    'Language changes immediately. Match selections and timer are kept.': ('Язык меняется сразу. Герой, карта и таймер сохраняются.', '语言立即切换，保留对战选择和计时器。', 'O idioma muda imediatamente. Seleções e tempo são mantidos.', 'El idioma cambia al instante. Selecciones y tiempo se conservan.', '語言立即切換，保留對戰選擇與計時器。', '언어가 즉시 변경되며 선택과 타이머는 유지됩니다.', 'La langue change immédiatement. Choix et chrono sont conservés.', 'Sprache wechselt sofort. Auswahl und Timer bleiben erhalten.'),
    'Advanced settings': ('Расширенные настройки', '高级设置', 'Configurações avançadas', 'Ajustes avanzados', '進階設定', '고급 설정', 'Paramètres avancés', 'Erweiterte Einstellungen'),
    'Defaults work for most players. Change these only when needed.': ('Большинству игроков подходят значения по умолчанию. Меняй их при необходимости.', '默认值适合大多数玩家，仅在需要时修改。', 'Os padrões atendem à maioria dos jogadores. Altere só se necessário.', 'Los valores iniciales sirven para la mayoría. Cámbialos si hace falta.', '預設值適合多數玩家，僅在需要時修改。', '기본값은 대부분의 플레이어에게 적합합니다. 필요할 때만 변경하세요.', 'Les valeurs par défaut conviennent à la plupart des joueurs.', 'Die Standardwerte passen für die meisten Spieler. Nur bei Bedarf ändern.'),
    'Discord connection': ('Подключение Discord', 'Discord 连接', 'Conexão Discord', 'Conexión Discord', 'Discord 連線', 'Discord 연결', 'Connexion Discord', 'Discord-Verbindung'),
    'Discord application ID': ('ID приложения Discord', 'Discord 应用 ID', 'ID do aplicativo Discord', 'ID de aplicación Discord', 'Discord 應用程式 ID', 'Discord 애플리케이션 ID', 'ID d’application Discord', 'Discord-Anwendungs-ID'),
    'Update interval (15–300 seconds)': ('Интервал обновления (15–300 секунд)', '更新间隔（15–300 秒）', 'Intervalo (15–300 segundos)', 'Intervalo (15–300 segundos)', '更新間隔（15–300 秒）', '갱신 간격 (15–300초)', 'Intervalle (15–300 secondes)', 'Aktualisierung (15–300 Sekunden)'),
    'Game process': ('Процесс игры', '游戏进程', 'Processo do jogo', 'Proceso del juego', '遊戲處理程序', '게임 프로세스', 'Processus du jeu', 'Spielprozess'),
    'Keep the default ID unless you own a Discord application. No account token is needed.': ('Оставь стандартный ID, если у тебя нет своего приложения Discord. Токен аккаунта не нужен.', '没有自己的 Discord 应用时请保留默认 ID，无需账号令牌。', 'Mantenha o ID padrão se não tiver um aplicativo Discord próprio. Não é necessário token.', 'Mantén el ID inicial si no tienes una aplicación Discord propia. No se necesita token.', '沒有自己的 Discord 應用程式時請保留預設 ID，無需帳號權杖。', 'Discord 앱을 소유하지 않았다면 기본 ID를 유지하세요. 계정 토큰은 필요 없습니다.', 'Gardez l’ID par défaut sauf si vous possédez une application Discord. Aucun jeton requis.', 'Standard-ID behalten, außer bei eigener Discord-Anwendung. Kein Konto-Token nötig.'),
    'Activity appearance': ('Оформление активности', '活动外观', 'Aparência da atividade', 'Aspecto de actividad', '活動外觀', '활동 모양', 'Apparence de l’activité', 'Darstellung der Aktivität'),
    'Use official hero portraits': ('Официальные портреты героев', '使用官方英雄头像', 'Usar retratos oficiais', 'Usar retratos oficiales', '使用官方英雄頭像', '공식 영웅 초상화 사용', 'Portraits officiels', 'Offizielle Heldenporträts'),
    'Use map artwork': ('Изображения карт', '使用地图图片', 'Usar imagens de mapas', 'Usar imágenes de mapas', '使用地圖圖片', '맵 이미지 사용', 'Images des cartes', 'Kartenbilder verwenden'),
    'Discord status line': ('Строка статуса Discord', 'Discord 状态行', 'Linha de status Discord', 'Línea de estado Discord', 'Discord 狀態列', 'Discord 상태 표시', 'Ligne de statut Discord', 'Discord-Statuszeile'),
    'Application name': ('Название приложения', '应用名称', 'Nome do aplicativo', 'Nombre de aplicación', '應用程式名稱', '앱 이름', 'Nom de l’application', 'Anwendungsname'),
    'State': ('Состояние', '状态', 'Estado', 'Estado', '狀態', '상태', 'État', 'Status'),
    'Details': ('Подробности', '详情', 'Detalhes', 'Detalles', '詳情', '상세 정보', 'Détails', 'Details'),
    'Fallback image key / HTTPS URL': ('Основная картинка: ключ или HTTPS URL', '备用图片键 / HTTPS URL', 'Imagem padrão: chave / URL HTTPS', 'Imagen inicial: clave / URL HTTPS', '備用圖片鍵 / HTTPS URL', '기본 이미지 키 / HTTPS URL', 'Image par défaut : clé / URL HTTPS', 'Standardbild: Schlüssel / HTTPS-URL'),
    'Custom hero image key / HTTPS URL': ('Своя картинка героя: ключ или HTTPS URL', '自定义英雄图片键 / HTTPS URL', 'Imagem do herói: chave / URL HTTPS', 'Imagen del héroe: clave / URL HTTPS', '自訂英雄圖片鍵 / HTTPS URL', '영웅 이미지 키 / HTTPS URL', 'Image du héros : clé / URL HTTPS', 'Heldenbild: Schlüssel / HTTPS-URL'),
    'Custom details (optional)': ('Свои подробности (необязательно)', '自定义详情（可选）', 'Detalhes personalizados (opcional)', 'Detalles propios (opcional)', '自訂詳情（選填）', '사용자 상세 정보 (선택)', 'Détails personnalisés (facultatif)', 'Eigene Details (optional)'),
    'Custom state (optional)': ('Свой статус (необязательно)', '自定义状态（可选）', 'Estado personalizado (opcional)', 'Estado propio (opcional)', '自訂狀態（選填）', '사용자 상태 (선택)', 'État personnalisé (facultatif)', 'Eigener Status (optional)'),
    'Button label (optional)': ('Название кнопки (необязательно)', '按钮文字（可选）', 'Texto do botão (opcional)', 'Texto del botón (opcional)', '按鈕文字（選填）', '버튼 이름 (선택)', 'Texte du bouton (facultatif)', 'Schaltflächentext (optional)'),
    'Button URL (http/https)': ('Ссылка кнопки (http/https)', '按钮 URL（http/https）', 'URL do botão (http/https)', 'URL del botón (http/https)', '按鈕 URL（http/https）', '버튼 URL (http/https)', 'URL du bouton (http/https)', 'Schaltflächen-URL (http/https)'),
    'Leave custom text blank to show mode, map and hero automatically. HTTPS artwork is fetched by Discord.': ('Оставь свой текст пустым, чтобы показывались режим, карта и герой. Картинки по HTTPS загружает Discord.', '自定义文字留空即可自动显示模式、地图和英雄。HTTPS 图片由 Discord 加载。', 'Deixe o texto vazio para mostrar modo, mapa e herói. Discord carrega as imagens HTTPS.', 'Deja el texto vacío para mostrar modo, mapa y héroe. Discord carga imágenes HTTPS.', '自訂文字留空即可自動顯示模式、地圖與英雄。HTTPS 圖片由 Discord 載入。', '사용자 텍스트를 비우면 모드, 맵, 영웅이 표시됩니다. HTTPS 이미지는 Discord가 불러옵니다.', 'Laissez le texte vide pour afficher mode, carte et héros. Discord charge les images HTTPS.', 'Eigene Texte leer lassen für Modus, Karte und Held. HTTPS-Bilder lädt Discord.'),
    'Experimental recognition': ('Экспериментальное распознавание', '实验性识别', 'Reconhecimento experimental', 'Reconocimiento experimental', '實驗性辨識', '실험적 인식', 'Reconnaissance expérimentale', 'Experimentelle Erkennung'),
    'Enable automatic hero/map recognition': ('Распознавать героя и карту автоматически', '启用自动英雄/地图识别', 'Reconhecer herói/mapa automaticamente', 'Reconocer héroe/mapa automáticamente', '啟用自動英雄/地圖辨識', '영웅/맵 자동 인식 사용', 'Reconnaître héros/carte automatiquement', 'Held/Karte automatisch erkennen'),
    'OCR reads visible English names on the primary monitor. It needs Tesseract and calibration; it cannot detect match phase or hidden text.': ('OCR читает видимые английские названия на основном мониторе. Нужны Tesseract и калибровка; фазу матча и скрытый текст он не определяет.', 'OCR 读取主显示器上的可见英文名称，需要 Tesseract 和校准，无法判断对战阶段或隐藏文字。', 'OCR lê nomes visíveis em inglês no monitor principal. Requer Tesseract e calibração; não detecta fase ou texto oculto.', 'OCR lee nombres visibles en inglés en el monitor principal. Requiere Tesseract y calibración; no detecta fase ni texto oculto.', 'OCR 讀取主螢幕上的可見英文名稱，需要 Tesseract 與校準，無法判斷對戰階段或隱藏文字。', 'OCR은 주 모니터의 영어 이름을 읽습니다. Tesseract와 보정이 필요하며 경기 단계나 숨긴 글자는 인식하지 못합니다.', 'L’OCR lit les noms anglais visibles sur l’écran principal. Tesseract et un calibrage sont requis; les phases et textes masqués ne sont pas détectés.', 'OCR liest sichtbare englische Namen auf dem Hauptmonitor. Tesseract und Kalibrierung nötig; Match-Phase und versteckter Text werden nicht erkannt.'),
    'Tesseract executable (blank = auto)': ('Путь к Tesseract (пусто = автоматически)', 'Tesseract 路径（留空 = 自动）', 'Executável Tesseract (vazio = automático)', 'Ejecutable Tesseract (vacío = automático)', 'Tesseract 路徑（留空 = 自動）', 'Tesseract 경로 (빈칸 = 자동)', 'Exécutable Tesseract (vide = auto)', 'Tesseract-Pfad (leer = automatisch)'),
    'OCR language (e.g. eng)': ('Язык OCR (например, eng)', 'OCR 语言（例如 eng）', 'Idioma OCR (ex.: eng)', 'Idioma OCR (ej.: eng)', 'OCR 語言（例如 eng）', 'OCR 언어 (예: eng)', 'Langue OCR (ex. eng)', 'OCR-Sprache (z. B. eng)'),
    'OCR interval (3–120 seconds)': ('Интервал OCR (3–120 секунд)', 'OCR 间隔（3–120 秒）', 'Intervalo OCR (3–120 segundos)', 'Intervalo OCR (3–120 segundos)', 'OCR 間隔（3–120 秒）', 'OCR 간격 (3–120초)', 'Intervalle OCR (3–120 secondes)', 'OCR-Intervall (3–120 Sekunden)'),
    'Select hero text region': ('Выбрать область имени героя', '选择英雄文字区域', 'Selecionar área do nome do herói', 'Elegir zona del nombre del héroe', '選擇英雄文字區域', '영웅 이름 영역 선택', 'Sélectionner la zone du héros', 'Bereich des Heldennamens wählen'),
    'Select map text region': ('Выбрать область названия карты', '选择地图文字区域', 'Selecionar área do nome do mapa', 'Elegir zona del nombre del mapa', '選擇地圖文字區域', '맵 이름 영역 선택', 'Sélectionner la zone de carte', 'Bereich des Kartennamens wählen'),
    'Not configured': ('Не настроено', '未配置', 'Não configurado', 'Sin configurar', '未設定', '설정 안 됨', 'Non configuré', 'Nicht eingerichtet'),
    'Clear': ('Сбросить', '清除', 'Limpar', 'Borrar', '清除', '지우기', 'Effacer', 'Zurücksetzen'),
    'Tesseract installation guide': ('Как установить Tesseract', 'Tesseract 安装指南', 'Guia de instalação Tesseract', 'Guía de instalación Tesseract', 'Tesseract 安裝指南', 'Tesseract 설치 안내', 'Guide d’installation Tesseract', 'Tesseract-Installationsanleitung'),
    'Open settings & logs': ('Открыть настройки и логи', '打开设置与日志', 'Abrir configurações e logs', 'Abrir ajustes y registros', '開啟設定與記錄', '설정 및 로그 열기', 'Ouvrir paramètres et journaux', 'Einstellungen und Protokolle öffnen'),
    'Quit OWRPC': ('Выйти из OWRPC', '退出 OWRPC', 'Sair do OWRPC', 'Salir de OWRPC', '結束 OWRPC', 'OWRPC 종료', 'Quitter OWRPC', 'OWRPC beenden'),
    'Open OWRPC': ('Открыть OWRPC', '打开 OWRPC', 'Abrir OWRPC', 'Abrir OWRPC', '開啟 OWRPC', 'OWRPC 열기', 'Ouvrir OWRPC', 'OWRPC öffnen'),
    'Cannot save settings': ('Не удалось сохранить настройки', '无法保存设置', 'Não foi possível salvar', 'No se pudieron guardar ajustes', '無法儲存設定', '설정을 저장할 수 없음', 'Enregistrement impossible', 'Speichern fehlgeschlagen'),
    'Invalid setting': ('Некорректная настройка', '设置无效', 'Configuração inválida', 'Ajuste no válido', '設定無效', '잘못된 설정', 'Paramètre invalide', 'Ungültige Einstellung'),
    'Enter a whole number for {field}.': ('В поле «{field}» нужно целое число.', '请为 {field} 输入整数。', 'Insira um número inteiro em {field}.', 'Introduce un número entero en {field}.', '請為 {field} 輸入整數。', '{field}에 정수를 입력하세요.', 'Saisissez un entier pour {field}.', 'Für {field} eine ganze Zahl eingeben.'),
    'Use a numeric Discord application ID (6–22 digits).': ('Укажи числовой ID приложения Discord (6–22 цифры).', '使用数字 Discord 应用 ID（6–22 位）。', 'Use um ID Discord numérico (6–22 dígitos).', 'Usa un ID Discord numérico (6–22 dígitos).', '使用數字 Discord 應用程式 ID（6–22 位）。', '숫자 Discord 앱 ID를 입력하세요 (6–22자리).', 'Utilisez un ID Discord numérique (6–22 chiffres).', 'Numerische Discord-Anwendungs-ID eingeben (6–22 Ziffern).'),
    'Button URL must be an http or https address.': ('Ссылка кнопки должна начинаться с http или https.', '按钮 URL 必须是 http 或 https 地址。', 'A URL do botão deve usar http ou https.', 'La URL del botón debe usar http o https.', '按鈕 URL 必須是 http 或 https 位址。', '버튼 URL은 http 또는 https 주소여야 합니다.', 'L’URL du bouton doit utiliser http ou https.', 'Die Schaltflächen-URL muss http oder https verwenden.'),
    'Cannot update Windows startup': ('Не удалось изменить автозапуск Windows', '无法更新 Windows 启动设置', 'Não foi possível alterar a inicialização', 'No se pudo cambiar el inicio de Windows', '無法更新 Windows 啟動設定', 'Windows 시작 설정 변경 실패', 'Modification du démarrage impossible', 'Windows-Autostart konnte nicht geändert werden'),
    'Settings recovered': ('Настройки восстановлены', '设置已恢复', 'Configurações recuperadas', 'Ajustes recuperados', '設定已恢復', '설정 복구됨', 'Paramètres récupérés', 'Einstellungen wiederhergestellt'),
    'Select text region': ('Выбор области текста', '选择文字区域', 'Selecionar área de texto', 'Elegir zona de texto', '選擇文字區域', '텍스트 영역 선택', 'Sélectionner la zone de texte', 'Textbereich wählen'),
    'Open the game on the primary monitor. Drag around one visible name, then press Enter. Escape cancels. The screenshot stays local.': ('Открой игру на основном мониторе. Выдели одно видимое название и нажми Enter. Escape отменяет. Снимок остаётся локальным.', '在主显示器打开游戏，框选一个可见名称后按 Enter。Escape 取消。截图仅在本地处理。', 'Abra o jogo no monitor principal. Selecione um nome visível e pressione Enter. Escape cancela. A captura fica local.', 'Abre el juego en el monitor principal. Selecciona un nombre visible y pulsa Enter. Escape cancela. La captura es local.', '在主螢幕開啟遊戲，框選一個可見名稱後按 Enter。Escape 取消。截圖僅在本機處理。', '주 모니터에서 게임을 여세요. 이름을 드래그로 선택한 뒤 Enter를 누르세요. Escape는 취소입니다. 캡처는 로컬에만 유지됩니다.', 'Ouvrez le jeu sur l’écran principal. Encadrez un nom puis Entrée. Échap annule. La capture reste locale.', 'Spiel auf dem Hauptmonitor öffnen. Einen Namen markieren, dann Enter. Escape bricht ab. Das Bild bleibt lokal.'),
    'Tray unavailable · window kept open': ('Трей недоступен · окно остаётся открытым', '托盘不可用 · 保持窗口打开', 'Bandeja indisponível · janela aberta', 'Bandeja no disponible · ventana abierta', '系統匣無法使用 · 保持視窗開啟', '트레이 사용 불가 · 창 유지', 'Zone de notification indisponible · fenêtre ouverte', 'Infobereich nicht verfügbar · Fenster bleibt offen'),
    'OCR is optional and disabled by default': ('OCR необязателен и по умолчанию выключен', 'OCR 可选，默认关闭', 'OCR opcional e desativado por padrão', 'OCR opcional y desactivado al inicio', 'OCR 為選用功能，預設關閉', 'OCR은 선택 기능이며 기본적으로 꺼져 있습니다', 'OCR optionnel, désactivé par défaut', 'OCR ist optional und standardmäßig deaktiviert'),
    'OCR waiting for match and Overwatch in foreground': ('OCR ждёт матча и активного окна Overwatch', 'OCR 等待对战和前台 Overwatch', 'OCR aguarda partida e Overwatch em primeiro plano', 'OCR espera partida y Overwatch en primer plano', 'OCR 等待對戰與前景 Overwatch', 'OCR은 경기와 오버워치 활성 창을 기다립니다', 'OCR en attente de partie et d’Overwatch au premier plan', 'OCR wartet auf Match und Overwatch im Vordergrund'),
    'Thank you Tominous and maxicc for the original OWRPC code.': ('Спасибо Tominous и maxicc за исходный код OWRPC.', '感谢 Tominous 和 maxicc 提供原始 OWRPC 代码。', 'Obrigado a Tominous e maxicc pelo código original do OWRPC.', 'Gracias a Tominous y maxicc por el código original de OWRPC.', '感謝 Tominous 與 maxicc 提供原始 OWRPC 程式碼。', '원본 OWRPC 코드를 제공한 Tominous와 maxicc에게 감사합니다.', 'Merci à Tominous et maxicc pour le code OWRPC original.', 'Danke an Tominous und maxicc für den ursprünglichen OWRPC-Code.'),
    'Unofficial fan companion. No game memory access, account login or screenshot uploads. Code: GPLv3.': ('Неофициальное фанатское приложение. Не читает память игры, не требует входа в аккаунт и не отправляет снимки экрана. Код: GPLv3.', '非官方粉丝助手，不读取游戏内存、不要求登录、不上传截图。代码：GPLv3。', 'Companheiro não oficial. Sem acesso à memória, login ou envio de capturas. Código: GPLv3.', 'Asistente no oficial. Sin acceso a memoria, inicio de sesión ni envío de capturas. Código: GPLv3.', '非官方粉絲助手，不讀取遊戲記憶體、不要求登入、不上傳截圖。程式碼：GPLv3。', '비공식 팬 도우미입니다. 게임 메모리 접근, 계정 로그인, 스크린샷 업로드가 없습니다. 코드: GPLv3.', 'Compagnon non officiel. Aucun accès mémoire, connexion de compte ou envoi de captures. Code : GPLv3.', 'Inoffizieller Fan-Begleiter. Kein Speicherzugriff, Konto-Login oder Screenshot-Upload. Code: GPLv3.'),
    '{heroes} heroes · {maps} maps · catalog as of {date}': ('{heroes} героев · {maps} карт · каталог на {date}', '{heroes} 位英雄 · {maps} 张地图 · 截止 {date}', '{heroes} heróis · {maps} mapas · catálogo de {date}', '{heroes} héroes · {maps} mapas · catálogo de {date}', '{heroes} 位英雄 · {maps} 張地圖 · 截至 {date}', '영웅 {heroes}명 · 맵 {maps}개 · {date} 기준', '{heroes} héros · {maps} cartes · catalogue au {date}', '{heroes} Helden · {maps} Karten · Stand {date}'),
    'GitHub & help': ('GitHub и помощь', 'GitHub 与帮助', 'GitHub e ajuda', 'GitHub y ayuda', 'GitHub 與說明', 'GitHub 및 도움말', 'GitHub et aide', 'GitHub und Hilfe'),
    'Quick Play': ('Быстрая игра', '快速游戏', 'Jogo rápido', 'Partida rápida', '快速對戰', '빠른 대전', 'Partie rapide', 'Schnellsuche'),
    'Competitive': ('Соревновательная игра', '竞技比赛', 'Competitivo', 'Competitiva', '競技對戰', '경쟁전', 'Compétitif', 'Rangliste'),
    'Stadium': ('Стадион', '角斗场', 'Estádio', 'Estadio', '競技場', '스타디움', 'Stade', 'Stadion'),
    'Arcade': ('Аркада', '街机先锋', 'Arcade', 'Arcade', '遊樂場', '아케이드', 'Arcade', 'Arcade'),
    'Custom Game': ('Своя игра', '自定义比赛', 'Jogo personalizado', 'Partida personalizada', '自訂遊戲', '사용자 지정 게임', 'Partie personnalisée', 'Benutzerdefiniertes Spiel'),
    'Mystery Heroes': ('Загадочные герои', '神秘英雄', 'Heróis misteriosos', 'Héroes misteriosos', '神秘英雄', '수수께끼의 영웅', 'Héros mystères', 'Überraschungshelden'),
    'Practice': ('Тренировка', '训练', 'Treino', 'Práctica', '練習', '훈련', 'Entraînement', 'Training'),
    'Control': ('Контроль', '控制', 'Controle', 'Control', '控制', '쟁탈', 'Contrôle', 'Kontrolle'),
    'Escort': ('Сопровождение', '护送', 'Escolta', 'Escolta', '護送', '호위', 'Escorte', 'Eskorte'),
    'Hybrid': ('Гибридный режим', '混合', 'Híbrido', 'Híbrido', '混合', '혼합', 'Hybride', 'Hybrid'),
    'Capture the Flag': ('Захват флага', '勇夺锦旗', 'Capture a bandeira', 'Captura la bandera', '搶旗', '깃발 뺏기', 'Capture du drapeau', 'Flaggeneroberung'),
    'Deathmatch': ('Схватка', '死斗', 'Combate até a morte', 'Combate a muerte', '死鬥', '데스매치', 'Combat à mort', 'Deathmatch'),
    'Team Deathmatch': ('Командная схватка', '团队死斗', 'Combate até a morte em equipe', 'Combate a muerte por equipos', '團隊死鬥', '팀 데스매치', 'Combat à mort par équipe', 'Team-Deathmatch'),
    'Elimination': ('Ликвидация', '决斗先锋', 'Eliminação', 'Eliminación', '淘汰賽', '섬멸전', 'Élimination', 'Eliminierung'),
    'Payload Race': ('Гонка грузов', '运载目标竞速', 'Corrida de carga', 'Carrera de carga', '運載目標競速', '화물 경주', 'Course de convoi', 'Frachtrennen'),
    'Workshop': ('Мастерская', '地图工坊', 'Oficina', 'Taller', '工作坊', '워크샵', 'Forge', 'Workshop'),
    'Mystery Madness: Graveyard Games': ('Загадочное безумие: игры на кладбище', '神秘狂欢：墓地游戏', 'Loucura misteriosa: jogos do cemitério', 'Locura misteriosa: juegos del cementerio', '神秘狂歡：墓地遊戲', '수수께끼 광기: 묘지 게임', 'Folie mystère : jeux du cimetière', 'Überraschungswahnsinn: Friedhofsspiele'),
}
_ROWS.update({'Show E/A/D from the scoreboard (experimental)': ('Показывать E/A/D с табло (экспериментально)', '显示记分板 E/A/D（实验性）', 'Mostrar E/A/D do placar (experimental)', 'Mostrar E/A/D del marcador (experimental)', '顯示計分板 E/A/D（實驗性）', '점수판 E/A/D 표시 (실험 기능)', 'Afficher E/A/D du tableau (expérimental)', 'E/A/D aus der Übersicht anzeigen (experimentell)'), 'KDA updates only while your scoreboard is visible. Select only your three E/A/D numbers. Old readings are omitted from Discord.': ('KDA обновляется, только когда видно табло. Выдели три своих числа E/A/D: устранения, помощи и смерти. Старые данные не отправляются в Discord.', 'KDA 仅在记分板可见时更新。只选择自己的三个 E/A/D 数字。过期数据不会发送到 Discord。', 'KDA atualiza apenas com o placar visível. Selecione somente seus três números E/A/D. Dados antigos não são enviados ao Discord.', 'KDA se actualiza solo con el marcador visible. Selecciona tus tres cifras E/A/D. Los datos antiguos no se envían a Discord.', 'KDA 僅在計分板可見時更新。只選取自己的三個 E/A/D 數字。過期資料不會傳送至 Discord。', '점수판이 보일 때만 KDA가 갱신됩니다. 자신의 E/A/D 숫자 세 개만 선택하세요. 오래된 값은 Discord에 전송하지 않습니다.', 'KDA se met à jour uniquement quand le tableau est visible. Sélectionnez vos trois nombres E/A/D. Les anciennes valeurs ne sont pas envoyées à Discord.', 'KDA wird nur bei sichtbarer Übersicht aktualisiert. Nur die eigenen drei E/A/D-Zahlen wählen. Alte Werte werden nicht an Discord gesendet.'), 'Select E/A/D region': ('Выбрать область E/A/D', '选择 E/A/D 区域', 'Selecionar área E/A/D', 'Seleccionar región E/A/D', '選取 E/A/D 區域', 'E/A/D 영역 선택', 'Sélectionner la zone E/A/D', 'E/A/D-Bereich wählen'), 'E/A/D {values} · read {seconds}s ago': ('E/A/D {values} · считано {seconds} с назад', 'E/A/D {values} · {seconds} 秒前读取', 'E/A/D {values} · lido há {seconds}s', 'E/A/D {values} · leído hace {seconds}s', 'E/A/D {values} · {seconds} 秒前讀取', 'E/A/D {values} · {seconds}초 전 읽음', 'E/A/D {values} · lu il y a {seconds}s', 'E/A/D {values} · vor {seconds}s gelesen'), 'E/A/D unavailable · open the scoreboard to refresh': ('E/A/D нет · открой табло для обновления', 'E/A/D 不可用 · 打开记分板刷新', 'E/A/D indisponível · abra o placar para atualizar', 'E/A/D no disponible · abre el marcador para actualizar', 'E/A/D 無法使用 · 開啟計分板更新', 'E/A/D 없음 · 점수판을 열어 새로 읽기', 'E/A/D indisponible · ouvrez le tableau pour actualiser', 'E/A/D nicht verfügbar · Übersicht zum Aktualisieren öffnen')})

_ROWS.update({'Enable automatic scene/hero/map recognition': ('Автоматически определять сцену, героя и карту', '自动识别场景、英雄和地图', 'Reconhecer cena, herói e mapa automaticamente', 'Detectar escena, héroe y mapa automáticamente', '自動辨識場景、英雄與地圖', '장면, 영웅, 지도 자동 인식', 'Détecter scène, héros et carte automatiquement', 'Szene, Held und Karte automatisch erkennen'), 'Windows OCR language (eng / rus)': ('Язык OCR Windows (eng / rus)', 'Windows OCR 语言 (eng / rus)', 'Idioma OCR do Windows (eng / rus)', 'Idioma OCR de Windows (eng / rus)', 'Windows OCR 語言 (eng / rus)', 'Windows OCR 언어 (eng / rus)', 'Langue OCR Windows (eng / rus)', 'Windows-OCR-Sprache (eng / rus)'), 'Game nickname (for your E/A/D row)': ('Ник в игре (для вашей строки E/A/D)', '游戏昵称（用于 E/A/D 行）', 'Apelido no jogo (linha E/A/D)', 'Nombre en el juego (fila E/A/D)', '遊戲暱稱（用於 E/A/D 列）', '게임 닉네임 (E/A/D 행)', 'Pseudo en jeu (ligne E/A/D)', 'Spielname (für deine E/A/D-Zeile)'), 'Automatic recognition uses Windows OCR on the foreground game window. Team colors are ignored. Enter your nickname for E/A/D.': ('Распознавание использует встроенный OCR Windows для активного окна игры. Цвета команд не учитываются. Для E/A/D укажите свой ник.', '使用 Windows OCR 读取当前游戏窗口，不依赖队伍颜色。输入昵称以读取 E/A/D。', 'Usa o OCR do Windows na janela ativa do jogo, sem depender das cores. Informe seu apelido para E/A/D.', 'Usa OCR de Windows en la ventana activa, sin depender del color. Introduce tu nombre para E/A/D.', '使用 Windows OCR 讀取目前遊戲視窗，不依賴隊伍顏色。輸入暱稱以讀取 E/A/D。', '활성 게임 창에서 Windows OCR을 사용하며 팀 색상에 의존하지 않습니다. E/A/D를 위해 닉네임을 입력하세요.', 'Utilise l’OCR Windows sur la fenêtre active, sans dépendre des couleurs. Saisissez votre pseudo pour E/A/D.', 'Verwendet Windows OCR im aktiven Spielfenster, unabhängig von Teamfarben. Gib deinen Namen für E/A/D ein.'), 'E/A/D is read from your nickname row while Tab is visible. Old readings are omitted from Discord. No region calibration is needed.': ('E/A/D считывается из строки с вашим ником при открытом Tab. Устаревшие значения скрываются в Discord. Выделять области не нужно.', '打开 Tab 时按昵称读取 E/A/D。旧数据不会显示在 Discord，无需设置区域。', 'Lê E/A/D na linha do seu apelido com Tab aberto. Oculta dados antigos no Discord. Não exige calibrar regiões.', 'Lee E/A/D en tu fila con Tab abierto. Oculta datos antiguos en Discord. No requiere calibrar regiones.', '開啟 Tab 時依暱稱讀取 E/A/D。舊資料不會顯示在 Discord，無須設定區域。', 'Tab 화면에서 닉네임 행의 E/A/D를 읽습니다. 오래된 값은 Discord에서 숨기며 영역 보정은 필요 없습니다.', 'Lit E/A/D sur votre ligne quand Tab est ouvert. Masque les anciennes valeurs dans Discord. Aucun calibrage requis.', 'Liest E/A/D in deiner Zeile bei geöffnetem Tab. Alte Werte werden in Discord ausgeblendet. Keine Bereichskalibrierung nötig.')})

_ROWS.update({
    'Solo': ('Соло', '单人', 'Solo', 'Solo', '單人', '솔로', 'Solo', 'Solo'),
    'In a party: {count} players': ('В группе: {count} игроков', '队伍人数：{count}', 'No grupo: {count} jogadores', 'En grupo: {count} jugadores', '隊伍人數：{count}', '그룹: {count}명', 'En groupe : {count} joueurs', 'In der Gruppe: {count} Spieler'),
    'In a party: {count} teammates': ('В группе: {count} игрока', '队伍人数：{count}', 'No grupo: {count} jogadores', 'En grupo: {count} jugadores', '隊伍人數：{count}', '그룹: {count}명', 'En groupe : {count} joueurs', 'In der Gruppe: {count} Spieler'),
})

_ROWS.update({'Additional': ('Дополнительно',
                '更多设置',
                'Mais opções',
                'Más opciones',
                '更多設定',
                '추가 설정',
                'Options supplémentaires',
                'Weitere Einstellungen'),
 'Current activity': ('Текущая активность',
                      '当前活动',
                      'Atividade atual',
                      'Actividad actual',
                      '目前活動',
                      '현재 활동',
                      'Activité actuelle',
                      'Aktuelle Aktivität'),
 'Party': ('Группа', '队伍', 'Grupo', 'Grupo', '隊伍', '그룹', 'Groupe', 'Gruppe'),
 'Match timer': ('Время матча',
                 '比赛时间',
                 'Tempo da partida',
                 'Tiempo de partida',
                 '對戰時間',
                 '경기 시간',
                 'Durée du match',
                 'Spielzeit'),
 'Automatic recognition': ('Автораспознавание',
                           '自动识别',
                           'Reconhecimento automático',
                           'Reconocimiento automático',
                           '自動辨識',
                           '자동 인식',
                           'Reconnaissance automatique',
                           'Automatische Erkennung'),
 'Waiting for recognition': ('Ожидание распознавания',
                             '等待识别',
                             'Aguardando reconhecimento',
                             'Esperando reconocimiento',
                             '等待辨識',
                             '인식 대기 중',
                             'En attente de reconnaissance',
                             'Warten auf Erkennung'),
 'Recognition reads the visible game. Open Tab to refresh the scoreboard.': ('Распознаётся видимый экран '
                                                                             'игры. Откройте Tab для '
                                                                             'обновления табло.',
                                                                             '识别可见的游戏画面。打开 Tab 更新记分板。',
                                                                             'Lê a tela visível do jogo. '
                                                                             'Abra Tab para atualizar o '
                                                                             'placar.',
                                                                             'Lee la pantalla visible. Abre '
                                                                             'Tab para actualizar el '
                                                                             'marcador.',
                                                                             '辨識可見遊戲畫面。開啟 Tab 更新計分板。',
                                                                             '보이는 게임 화면을 읽습니다. Tab을 열어 점수판을 '
                                                                             '갱신하세요.',
                                                                             'Lit l’écran visible du jeu. '
                                                                             'Ouvrez Tab pour actualiser les '
                                                                             'scores.',
                                                                             'Liest den sichtbaren '
                                                                             'Spielbildschirm. Tab öffnet '
                                                                             'die aktuelle Punktetafel.'),
 'Manual correction': ('Ручная корректировка',
                       '手动调整',
                       'Ajuste manual',
                       'Ajuste manual',
                       '手動調整',
                       '수동 수정',
                       'Correction manuelle',
                       'Manuelle Anpassung'),
 'Choose': ('Выбрать', '选择', 'Escolher', 'Elegir', '選擇', '선택', 'Choisir', 'Auswählen'),
 'Preview examples': ('Примеры отображения',
                      '预览示例',
                      'Exemplos de prévia',
                      'Ejemplos de vista previa',
                      '預覽範例',
                      '미리보기 예시',
                      'Exemples d’affichage',
                      'Vorschaubeispiele'),
 'Live': ('Сейчас', '实时', 'Agora', 'Actual', '即時', '현재', 'En direct', 'Aktuell'),
 'Live activity': ('Ваш текущий статус',
                   '当前状态',
                   'Seu status atual',
                   'Tu estado actual',
                   '目前狀態',
                   '현재 상태',
                   'Votre statut actuel',
                   'Dein aktueller Status'),
 'Example — {scene}': ('Пример · {scene}',
                       '示例 · {scene}',
                       'Exemplo · {scene}',
                       'Ejemplo · {scene}',
                       '範例 · {scene}',
                       '예시 · {scene}',
                       'Exemple · {scene}',
                       'Beispiel · {scene}'),
 'Examples only change the preview. Your Discord activity stays live.': ('Примеры меняют только превью. '
                                                                         'Статус в Discord остаётся текущим.',
                                                                         '示例只更改预览，不影响 Discord 状态。',
                                                                         'Os exemplos só mudam a prévia, não '
                                                                         'o status no Discord.',
                                                                         'Los ejemplos solo cambian la vista '
                                                                         'previa, no el estado en Discord.',
                                                                         '範例只改變預覽，不影響 Discord 狀態。',
                                                                         '예시는 미리보기만 변경하며 Discord 상태에는 영향을 주지 '
                                                                         '않습니다.',
                                                                         'Les exemples changent uniquement '
                                                                         'l’aperçu, pas le statut Discord.',
                                                                         'Beispiele ändern nur die Vorschau, '
                                                                         'nicht den Discord-Status.'),
 'Your activity updates automatically': ('Активность обновляется автоматически',
                                         '活动自动更新',
                                         'Sua atividade é atualizada automaticamente',
                                         'Tu actividad se actualiza automáticamente',
                                         '活動自動更新',
                                         '활동이 자동으로 갱신됩니다',
                                         'Votre activité se met à jour automatiquement',
                                         'Deine Aktivität wird automatisch aktualisiert'),
 'Manual activity': ('Ручной режим',
                     '手动模式',
                     'Modo manual',
                     'Modo manual',
                     '手動模式',
                     '수동 모드',
                     'Mode manuel',
                     'Manueller Modus'),
 'Menu logo HTTPS URL': ('HTTPS-ссылка на логотип в меню',
                         '菜单标志 HTTPS 地址',
                         'URL HTTPS do logo no menu',
                         'URL HTTPS del logo del menú',
                         '選單標誌 HTTPS 網址',
                         '메뉴 로고 HTTPS URL',
                         'URL HTTPS du logo du menu',
                         'HTTPS-URL des Menülogos'),
 'Recognition settings': ('Настройки распознавания',
                          '识别设置',
                          'Configurações de reconhecimento',
                          'Ajustes de reconocimiento',
                          '辨識設定',
                          '인식 설정',
                          'Réglages de reconnaissance',
                          'Erkennungseinstellungen'),
 'This is a local preview. Discord controls the final appearance.': ('Локальное превью. Окончательное '
                                                                     'оформление зависит от Discord.',
                                                                     '这是本地预览，最终外观由 Discord 决定。',
                                                                     'Prévia local. A aparência final '
                                                                     'depende do Discord.',
                                                                     'Vista previa local. Discord determina '
                                                                     'la apariencia final.',
                                                                     '這是本機預覽，最終外觀由 Discord 決定。',
                                                                     '로컬 미리보기이며 최종 모습은 Discord에서 결정합니다.',
                                                                     'Aperçu local. L’affichage final dépend '
                                                                     'de Discord.',
                                                                     'Lokale Vorschau. Discord bestimmt das '
                                                                     'endgültige Aussehen.'),
 'Custom artwork is sent to Discord; the preview uses local artwork.': ('В Discord отправляется ваша '
                                                                        'картинка; здесь показана локальная.',
                                                                        '自定义图片发送到 Discord；预览使用本地图片。',
                                                                        'Sua imagem é enviada ao Discord; a '
                                                                        'prévia usa a imagem local.',
                                                                        'Tu imagen se envía a Discord; la '
                                                                        'vista previa usa la imagen local.',
                                                                        '自訂圖片傳送至 Discord；預覽使用本機圖片。',
                                                                        '사용자 이미지는 Discord로 전송되며 미리보기는 로컬 '
                                                                        '이미지를 씁니다.',
                                                                        'Votre image est envoyée à Discord ; '
                                                                        'l’aperçu utilise l’image locale.',
                                                                        'Dein Bild wird an Discord gesendet; '
                                                                        'die Vorschau nutzt lokale Bilder.'),
 'The menu logo is ready locally. Add its public HTTPS URL in Additional to show it in Discord.': ('Логотип '
                                                                                                   'готов. '
                                                                                                   'Для '
                                                                                                   'показа в '
                                                                                                   'Discord '
                                                                                                   'нужна '
                                                                                                   'публичная '
                                                                                                   'HTTPS-ссылка '
                                                                                                   'в '
                                                                                                   '«Дополнительно».',
                                                                                                   '标志已准备好。在更多设置中添加公共 '
                                                                                                   'HTTPS '
                                                                                                   '地址以在 '
                                                                                                   'Discord '
                                                                                                   '显示。',
                                                                                                   'Logo '
                                                                                                   'pronto. '
                                                                                                   'Adicione '
                                                                                                   'uma URL '
                                                                                                   'HTTPS '
                                                                                                   'pública '
                                                                                                   'em Mais '
                                                                                                   'opções '
                                                                                                   'para '
                                                                                                   'exibi-lo '
                                                                                                   'no '
                                                                                                   'Discord.',
                                                                                                   'Logo '
                                                                                                   'listo. '
                                                                                                   'Añade '
                                                                                                   'una URL '
                                                                                                   'HTTPS '
                                                                                                   'pública '
                                                                                                   'en Más '
                                                                                                   'opciones '
                                                                                                   'para '
                                                                                                   'mostrarlo '
                                                                                                   'en '
                                                                                                   'Discord.',
                                                                                                   '標誌已備妥。在更多設定加入公開 '
                                                                                                   'HTTPS '
                                                                                                   '網址以在 '
                                                                                                   'Discord '
                                                                                                   '顯示。',
                                                                                                   '로고가 '
                                                                                                   '준비되었습니다. '
                                                                                                   '추가 설정에 '
                                                                                                   '공개 HTTPS '
                                                                                                   'URL을 넣으면 '
                                                                                                   'Discord에 '
                                                                                                   '표시됩니다.',
                                                                                                   'Logo '
                                                                                                   'prêt. '
                                                                                                   'Ajoutez '
                                                                                                   'son URL '
                                                                                                   'HTTPS '
                                                                                                   'publique '
                                                                                                   'dans les '
                                                                                                   'options '
                                                                                                   'pour '
                                                                                                   'l’afficher '
                                                                                                   'dans '
                                                                                                   'Discord.',
                                                                                                   'Logo '
                                                                                                   'bereit. '
                                                                                                   'Trage '
                                                                                                   'die '
                                                                                                   'öffentliche '
                                                                                                   'HTTPS-URL '
                                                                                                   'in den '
                                                                                                   'weiteren '
                                                                                                   'Einstellungen '
                                                                                                   'für '
                                                                                                   'Discord '
                                                                                                   'ein.')})

_ROWS.update({
    'E/A/D is read from your nickname row while Tab is visible. Discord keeps the last confirmed values until the next update or match exit. No region calibration is needed.': (
        'E/A/D считывается из строки с вашим ником при открытом Tab. Discord сохраняет последние подтверждённые значения до обновления или выхода из матча. Выделять области не нужно.',
        '打开 Tab 时按昵称读取 E/A/D。Discord 保留最后确认的数值，直到下次更新或离开比赛。无需设置区域。',
        'Lê E/A/D na linha do seu apelido com Tab aberto. Discord mantém os últimos valores confirmados até atualizar ou sair da partida. Não exige calibrar regiões.',
        'Lee E/A/D en tu fila con Tab abierto. Discord conserva los últimos valores confirmados hasta actualizar o salir de la partida. No requiere calibrar regiones.',
        '開啟 Tab 時依暱稱讀取 E/A/D。Discord 保留最後確認的數值，直到下次更新或離開比賽。無須設定區域。',
        'Tab 화면에서 닉네임 행의 E/A/D를 읽습니다. Discord는 다음 갱신이나 경기 종료까지 마지막 확인 값을 유지합니다. 영역 보정은 필요 없습니다.',
        'Lit E/A/D sur votre ligne quand Tab est ouvert. Discord conserve les dernières valeurs confirmées jusqu’à la prochaine mise à jour ou la sortie du match. Aucun calibrage requis.',
        'Liest E/A/D in deiner Zeile bei geöffnetem Tab. Discord behält die zuletzt bestätigten Werte bis zur nächsten Aktualisierung oder zum Verlassen des Matches. Keine Bereichskalibrierung nötig.'),
    'Choosing a hero': ('Выбор героя', '选择英雄', 'Escolhendo herói', 'Eligiendo héroe', '選擇英雄', '영웅 선택', 'Choix du héros', 'Heldenauswahl'),
    'Waiting for group': ('Ожидание группы', '等待队伍', 'Aguardando o grupo', 'Esperando al grupo', '等待隊伍', '그룹 대기', 'En attente du groupe', 'Warten auf die Gruppe'),
    'Loading map': ('Загрузка карты', '加载地图', 'Carregando mapa', 'Cargando mapa', '載入地圖', '지도 로딩', 'Chargement de la carte', 'Karte wird geladen'),
    'Match finished': ('Матч завершён', '比赛结束', 'Partida encerrada', 'Partida terminada', '比賽結束', '경기 종료', 'Partie terminée', 'Match beendet'),
    'Discord artwork layout': ('Иконки Discord', 'Discord 图片布局', 'Imagens do Discord', 'Imágenes de Discord', 'Discord 圖片配置', 'Discord 이미지 배치', 'Images Discord', 'Discord-Bildanordnung'),
    'Large map, small hero': ('Большая карта, маленький герой', '大地图，小英雄', 'Mapa grande, herói pequeno', 'Mapa grande, héroe pequeño', '大地圖，小英雄', '큰 지도, 작은 영웅', 'Grande carte, petit héros', 'Große Karte, kleiner Held'),
    'Large hero, small map': ('Большой герой, маленькая карта', '大英雄，小地图', 'Herói grande, mapa pequeno', 'Héroe grande, mapa pequeño', '大英雄，小地圖', '큰 영웅, 작은 지도', 'Grand héros, petite carte', 'Großer Held, kleine Karte'),
})
TEXT = {key: dict(zip(LANGUAGES, (key, *values))) for key, values in _ROWS.items()}


TEXT.update({key: dict(zip(LANGUAGES, (key, *values))) for key, values in {'Recognition language': ['Язык распознавания', '识别语言', 'Idioma de reconhecimento', 'Idioma de reconocimiento', '辨識語言', '인식 언어', 'Langue de reconnaissance', 'Erkennungssprache'], 'Check GitHub releases on startup': ['Проверять обновления при запуске', '启动时检查更新', 'Verificar atualizações ao iniciar', 'Buscar actualizaciones al iniciar', '啟動時檢查更新', '시작 시 업데이트 확인', 'Vérifier les mises à jour au démarrage', 'Beim Start nach Updates suchen'], 'Refresh hero and map catalog daily': ['Обновлять справочник героев и карт ежедневно', '每天更新英雄和地图目录', 'Atualizar catálogo de heróis e mapas diariamente', 'Actualizar catálogo de héroes y mapas a diario', '每天更新英雄與地圖目錄', '영웅 및 전장 목록 매일 갱신', 'Actualiser le catalogue chaque jour', 'Helden- und Kartenkatalog täglich aktualisieren'], 'Check for updates': ['Проверить обновления', '检查更新', 'Verificar atualizações', 'Buscar actualizaciones', '檢查更新', '업데이트 확인', 'Vérifier les mises à jour', 'Nach Updates suchen'], 'Refresh catalog': ['Обновить справочник', '更新目录', 'Atualizar catálogo', 'Actualizar catálogo', '更新目錄', '목록 갱신', 'Actualiser le catalogue', 'Katalog aktualisieren'], 'Network unavailable; saved data retained': ['Сеть недоступна. Используются сохранённые данные', '网络不可用，保留已保存的数据', 'Rede indisponível; dados salvos mantidos', 'Red no disponible; datos guardados conservados', '網路無法使用，保留已儲存資料', '네트워크 연결 불가; 저장된 데이터 유지', 'Réseau indisponible ; données conservées', 'Netzwerk nicht verfügbar; gespeicherte Daten bleiben erhalten'], 'Update available': ['Доступно обновление', '有可用更新', 'Atualização disponível', 'Actualización disponible', '有可用更新', '업데이트 사용 가능', 'Mise à jour disponible', 'Update verfügbar'], 'No newer release available': ['Новых релизов нет', '没有新版本', 'Nenhuma versão mais recente', 'No hay una versión más reciente', '沒有新版本', '새 버전 없음', 'Aucune version plus récente', 'Keine neuere Version verfügbar'], 'Catalog updated': ['Справочник обновлён', '目录已更新', 'Catálogo atualizado', 'Catálogo actualizado', '目錄已更新', '목록 갱신 완료', 'Catalogue actualisé', 'Katalog aktualisiert'], 'Open the release page?': ['Открыть страницу релиза?', '打开版本页面？', 'Abrir a página da versão?', '¿Abrir la página de la versión?', '開啟版本頁面？', '릴리스 페이지를 여시겠습니까?', 'Ouvrir la page de la version ?', 'Versionsseite öffnen?'], 'Checking…': ['Проверка…', '正在检查…', 'Verificando…', 'Comprobando…', '正在檢查…', '확인 중…', 'Vérification…', 'Prüfung…'], 'An error occurred; see logs': ['Произошла ошибка. Подробности в журнале', '发生错误，请查看日志', 'Ocorreu um erro; consulte os logs', 'Se produjo un error; consulta los registros', '發生錯誤，請查看記錄', '오류 발생; 로그 확인', 'Une erreur est survenue ; consultez les journaux', 'Fehler aufgetreten; siehe Protokoll']} .items()})

def tr(key, language='en', **values):
    translated = TEXT.get(key, {}).get(resolve_language(language), key)
    return translated.format(**values) if values else translated
