"""One derived activity snapshot for all interactive audio/resource interlocks.

StudioApp.control_lock serializes every reservation/start/stop. This module does
not maintain a second recording state: it derives capabilities from service truth.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AppActivity:
    maintenance: bool = False
    recording: bool = False
    paused: bool = False
    live: str = 'idle'
    live_reserved: bool = False
    microphone_test: bool = False
    speaker_test: bool = False
    alarm: bool = False
    bluetooth: bool = False
    download: bool = False
    model_test: bool = False
    pending: bool = False

    @property
    def live_busy(self):
        return self.live_reserved or self.live in ('connecting','active','stopping','listening','thinking','speaking','reconnecting','closing')

    @property
    def alarm_allowed(self):
        # A timer must be audible during Live, even while the assistant speaks.
        # Recordings/tests and device changes retain exclusive audio ownership.
        return not (self.maintenance or self.recording or self.microphone_test or self.speaker_test or
                    self.alarm or self.download or self.model_test or self.bluetooth)

    @property
    def occupied(self):
        return self.maintenance or self.recording or self.live_busy or self.microphone_test or self.speaker_test or self.alarm or self.download or self.model_test or self.bluetooth

    @property
    def mode(self):
        if self.maintenance:return 'maintenance'
        if self.recording:return 'paused' if self.paused else 'recording'
        if self.live_busy:return 'live-connecting' if self.live in ('connecting','reconnecting') else 'live-stopping' if self.live in ('closing','stopping') else 'live-active'
        if self.microphone_test:return 'microphone-test'
        if self.alarm:return 'alarm'
        if self.speaker_test:return 'speaker-test'
        if self.bluetooth:return 'bluetooth'
        if self.model_test:return 'model-test'
        if self.download:return 'download'
        return 'idle'

    @property
    def reason(self):
        return {'maintenance':'Gerät wird gewartet. Bitte kurz warten.', 'recording':'Aufnahme läuft.', 'paused':'Aufnahme pausiert. Bitte zuerst stoppen.',
                'live-connecting':'Live-Gespräch wird verbunden.', 'live-active':'Live-Gespräch läuft. Bitte zuerst beenden.',
                'live-stopping':'Live-Gespräch wird beendet.', 'microphone-test':'Mikrofontest läuft.',
                'alarm':'Timer-Alarm läuft. Über „Alarm stoppen“ beenden.', 'speaker-test':'Lautsprechertest läuft.', 'model-test':'Modelltest läuft.',
                'bluetooth':'Bluetooth wird eingerichtet. Bitte abschließen oder abbrechen.', 'download':'Modelldownload läuft.', 'idle':''}[self.mode]

    def public(self):
        return {'mode':self.mode, 'busy':bool(self.occupied), 'reason':self.reason,
                'recording':self.recording, 'live_busy':self.live_busy}

    def capabilities(self, *, low_disk=False, needs_login=False, setup_complete=False, brain_signed_in=False):
        def rule(allowed, why=''):
            return {'allowed':bool(allowed), 'reason':'' if allowed else why}
        reason=self.reason
        return {
            'record':rule(not self.occupied and not low_disk and not needs_login and setup_complete,
                          reason or ('Microsoft anmelden oder Verarbeitung auf lokal stellen.' if needs_login else 'Zu wenig freier Speicher.' if low_disk else 'Mikrofon zuerst einrichten.')),
            'configure':rule(not self.occupied,reason),
            'probe':rule(not self.occupied and not low_disk,reason or 'Zu wenig freier Speicher.'),
            'install':rule(not self.occupied and not self.pending,reason or 'Offene Verarbeitung zuerst abschließen.'),
            'model_test':rule(not self.occupied and not self.pending and not low_disk,reason or ('Zu wenig freier Speicher.' if low_disk else 'Offene Verarbeitung zuerst abschließen.')),
            'finish_setup':rule(not self.occupied,reason),
            'process':rule(not self.maintenance and not self.recording and not self.live_busy and not self.download and not self.model_test and not self.bluetooth,reason),
            'live':rule(not self.occupied and brain_signed_in,reason or 'Bitte zuerst beim Brain-Konto anmelden.'),
        }
