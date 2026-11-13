"""Panel integration checks without network access or a panel installation."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from backend import tuik_jobs
from scraper import bot, panel_tuik, panel_yokatlas


def monitor(settings=None):
    result = Mock(settings=settings or {}, retry_requests=[])
    result.should_stop.return_value = False
    return result


class PanelTests(unittest.TestCase):
    def test_tuik_csv_negotiation_and_turkish_city_names(self):
        response = Mock(status=200)
        response.read.return_value = b'TIME_PERIOD,OBS_VALUE\n2025,42\n'
        with patch.object(tuik_jobs.urllib.request, 'urlopen') as urlopen:
            urlopen.return_value.__enter__.return_value = response
            tuik_jobs._download(tuik_jobs.SDMX_URL + '/data/TR,DF_ADNKS_T16,1.0?format=SDMX-CSV')
        self.assertEqual(urlopen.call_args.args[0].get_header('Accept'), 'text/csv')
        self.assertEqual(tuik_jobs._normalize('Şanlıurfa'), tuik_jobs._normalize('ŞANLIURFA'))

    def test_yokatlas_stop_during_delay_prevents_next_request(self):
        panel = monitor()
        panel.should_stop.return_value = True
        api = bot.API(SimpleNamespace(bot=panel, retries=0, delay=2, max_requests=10, timeout=20))
        self.addCleanup(api.session.close)
        with patch.object(api.session, 'request') as request, self.assertRaises(KeyboardInterrupt):
            api.fetch('GET', '/api/parameters/yil', None)
        request.assert_not_called()

    def test_yokatlas_retry_resolves_original_failed_request(self):
        panel = monitor()
        panel.retry_requests = [{'request_key': '/api/parameters/yil:null', 'failed_id': 7}]
        api = bot.API(SimpleNamespace(bot=panel, retries=0, delay=2, max_requests=10, timeout=20))
        self.addCleanup(api.session.close)
        response = SimpleNamespace(status_code=200, headers={'Content-Type': 'text/plain;charset=UTF-8'}, content=b'2026')
        with patch.object(api.session, 'request', return_value=response):
            self.assertEqual(api.fetch('GET', '/api/parameters/yil', None), b'2026')
        panel.request_ok.assert_called_once_with(failed_id=7)

    def test_yokatlas_invalid_settings_do_not_start_collection(self):
        for settings in ({'arsiv_dizini': '../outside'}, {'bekleme_saniye': float('nan')},
                         {'sayfa_boyutu': 101}, {'sadece_arsiv': 'false'}):
            with self.subTest(settings=settings), patch.object(panel_yokatlas, 'cycle') as cycle:
                with self.assertRaises(ValueError):
                    panel_yokatlas.run(monitor(settings))
                cycle.assert_not_called()

    def test_tuik_retry_uses_previous_year_even_after_settings_change(self):
        retries = [{'request_key': 'https://nsiws.tuik.gov.tr/rest/data/TR,DF_ADNKS_T16,1.0?startPeriod=2024&endPeriod=2024'}]
        self.assertEqual(panel_tuik.targets({'yil': 2025}, retries), [('DF_ADNKS_T16', '1.0', 2024)])

    def test_tuik_failed_auth_does_not_store_secret_in_retry_request(self):
        panel = monitor()
        with patch.object(tuik_jobs, '_download', side_effect=tuik_jobs.TuikError('Erişim reddedildi.')):
            with self.assertRaises(tuik_jobs.TuikError):
                tuik_jobs._read(tuik_jobs.TOKEN_URL, form={'api_key': 'secret-value'}, monitor=panel)
        self.assertNotIn('secret-value', str(panel.request_failed.call_args))
        panel.request_ok.assert_not_called()

    def test_tuik_database_uses_ingestion_secret_and_docker_host(self):
        with patch.dict(os.environ, {'PGHOST': 'postgres', 'PGPORT': '5432',
                                    'ATLAS_INGEST_PASSWORD': 'ingest-secret',
                                    'ADMIN_DATABASE_URL': 'panel-secret'}):
            with patch.object(tuik_jobs.psycopg, 'connect') as connect:
                tuik_jobs._db_connect()
        self.assertEqual(connect.call_args.kwargs['host'], 'postgres')
        self.assertEqual(connect.call_args.kwargs['user'], 'atlas_ingest')
        self.assertEqual(connect.call_args.kwargs['password'], 'ingest-secret')

    def test_tuik_failed_ingestion_cannot_be_reported_successful(self):
        dataset = {'id': 'DF_ADNKS_T16', 'version': '1.0', 'title': 'Nüfus'}
        with patch.dict(os.environ, {}), patch.object(tuik_jobs, 'list_datasets', return_value=[dataset]), \
                patch.object(tuik_jobs, 'create_run', return_value=10), \
                patch.object(tuik_jobs, 'run_ingestion'), \
                patch.object(tuik_jobs, 'get_run', return_value={'status': 'failed', 'message': 'DB failed'}):
            with self.assertRaisesRegex(RuntimeError, 'DB failed'):
                panel_tuik.run(monitor())


if __name__ == '__main__':
    unittest.main()
