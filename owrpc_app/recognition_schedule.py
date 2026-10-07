"""Bounded, foreground-only recognition bursts without keyboard hooks."""


class RecognitionSchedule:
    def __init__(self):
        self.next_poll = 0
        self.followup = None
        self.pressed = False
        self.cooldown = 0
        self.burst_attempt = 0

    def due(self, now, active, tab, interval):
        rising = active and tab and not self.pressed
        self.pressed = active and tab
        if not active or not tab:
            self.followup = None
            self.burst_attempt = 0
        if not active or now < self.cooldown:
            return False
        if rising:
            self.burst_attempt = 1
            # completed() schedules the second capture relative to completion.
            self.followup = float("inf")
            self.next_poll = now + interval
            return True
        if self.followup is not None and now >= self.followup:
            self.followup = None
            self.burst_attempt += 1
            self.next_poll = now + interval
            return True
        if now >= self.next_poll:
            self.burst_attempt = 0
            self.next_poll = now + interval
            return True
        return False

    def completed(self, now, interval):
        self.next_poll = now + interval
        if self.followup is not None:
            self.followup = now

    def retry_followup(self, now):
        # One bounded recovery when an opening/fading frame misses the title.
        # Never turn a held Tab into continuous fast capture.
        if self.pressed and self.burst_attempt == 2:
            self.followup = now + 0.10

    def failed(self, now):
        self.followup = None
        self.burst_attempt = 0
        self.cooldown = self.next_poll = now + 30
