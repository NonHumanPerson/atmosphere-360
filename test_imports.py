import sys
sys.path.insert(0, '.')

from config import USER_MODES, APP_NAME
print('APP_NAME:', APP_NAME)
print('USER_MODES:', USER_MODES)

from serpapi_client import SerpApiClient
print('serpapi_client OK')

from src.llm import get_gemini_client, GeminiClient, GeminiResponse
print('llm/gemini OK')

from src.utils.cadr_calculator import calculate_required_cadr
print('cadr_calculator OK')

from src.data.sqlite_store import create_complaint
print('sqlite_store OK')

from src.citizen.my_air import render_my_air_tab
print('my_air OK')

from src.citizen.purifier_match import render_purifier_match_tab, PURIFIER_DATABASE
print(f'purifier_match OK ({len(PURIFIER_DATABASE)} products)')

from src.officer.civic_pulse import render_civic_pulse_tab
print('civic_pulse OK')

from src.officer.command_center import render_command_center_tab
print('command_center OK')

from src.enterprise.airsense import render_airsense_tab
print('airsense OK')

from src.admin.admin_panel import render_admin_panel
print('admin_panel OK')

from src.ingest.live_feed import build_live_context
print('live_feed OK')

print()
print('All imports successful!')