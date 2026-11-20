"""Touch regression on an isolated Studio preview. Requires Playwright and Chrome."""
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Thread

from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.studio_preview import create_preview
from services.cdb_integration import CdbFailure
from web_server import StudioServer


class TestBrain:
    approved = False
    codes = 0

    def request(self, url, *args, **kwargs):
        if url.endswith('/devicecode'):
            self.codes += 1
            return dict(device_code='test-device', user_code='TEST-CODE',
                        verification_uri='https://login.microsoft.com/device', expires_in=900)
        if url.endswith('/token'):
            if not self.approved:
                raise CdbFailure('authorization_pending')
            return dict(access_token='synthetic', token_type='Bearer', expires_in=3600)
        if url.endswith('/auth/me'):
            return dict(is_active=True, user_id='synthetic', display_name='Alexandra Mustername',
                        client_id='11111111-1111-1111-1111-111111111111')
        if '/knowledge-areas?' in url:
            return []
        raise CdbFailure('Im Test offline.')


def check_screen(browser, width, height, root):
    app = create_preview(root, delay=.1)
    # The preview records generated PCM and processes it with its synthetic backend.
    setup = app.setup_state()
    for check in setup['checks']:
        check['ok'] = True
    app.setup_state = lambda: dict(setup, ready=True)
    brain = TestBrain()
    app.cdb.transport = brain
    if width == 1280:
        app.cdb.configure({'server':'https://cdbos.de'})
    server = StudioServer(('127.0.0.1', 0), app)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    page = browser.new_page(viewport={'width':width, 'height':height}, has_touch=True)
    try:
        page.goto(f'http://127.0.0.1:{server.server_port}')
        chip = page.locator('#account-shortcut')
        action = page.locator('#account-action')
        close = page.locator('#account-close')
        expect(page.locator('#start-view')).to_be_visible()
        expect(chip).to_contain_text('Produktion' if width == 1280 else 'Staging')
        chip.tap()
        qr = page.locator('#account-qr')
        expect(qr).to_be_visible()
        expect(page.locator('#account-code')).to_have_text('TEST-CODE')
        assert qr.evaluate('el => el.complete && el.naturalWidth > 0')
        assert qr.bounding_box()['width'] >= 312
        assert action.bounding_box()['y'] + action.bounding_box()['height'] <= height
        close.tap()
        chip.tap()
        assert brain.codes == 1
        action.tap()
        expect(action).to_have_text('Anmeldecode anzeigen')
        brain.approved = True
        action.tap()
        expect(chip).to_contain_text('Alexandra Mustername', timeout=12000)
        expect(action).to_have_text('Abmelden')
        close.tap()

        page.locator('#start-recorder').tap()
        expect(page.locator('#capture-pause')).to_be_visible()
        expect(page.locator('#duration')).not_to_have_text('00:00')
        for paused in (False, True):
            if paused:
                page.locator('#capture-pause').tap()
            chip.tap()
            expect(action).to_be_disabled()
            expect(page.locator('#account-message')).to_contain_text('pausiert' if paused else 'Aufnahme läuft')
            close.tap()
        page.locator('#record').tap()
        expect(page.locator('#capture-controls')).to_be_hidden()
        lease = app.action('/api/live/reserve', {'area_ids':['22222222-2222-2222-2222-222222222222']})['lease']
        try:
            chip.tap()
            expect(action).to_be_disabled()
            expect(page.locator('#account-message')).to_contain_text('Live-Gespräch')
            close.tap()
        finally:
            app.action('/api/live/end', {'lease':lease})
        chip.tap()
        expect(action).to_be_enabled()
        action.tap()
        expect(chip).to_contain_text('Brain anmelden')
        assert app.cdb.public()['identity'] is None
    finally:
        page.close()
        server.shutdown()
        worker.join()
        server.server_close()
        app.close()


if __name__ == '__main__':
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='chrome', args=['--mute-audio'])
        try:
            for width, height in ((1024, 600), (1280, 720)):
                with TemporaryDirectory() as root:
                    check_screen(browser, width, height, root)
                print(f'{width} × {height} bestanden', flush=True)
        finally:
            browser.close()
