import json,unittest
from pathlib import Path
from unittest.mock import Mock,patch
import pandas as pd
from src.activities import matching_parks
from src.assistant import activity_fallback,retrieve,fact_text,interpret,enforce_named_park_scope,validate_plan
from src.database import COLUMNS
Q='Where is a good national park that has climbing activities?'
class ActivityTests(unittest.TestCase):
 def setUp(self):
  self.profiles=json.loads((Path(__file__).resolve().parents[1]/'data/park_profiles.json').read_text(encoding='utf-8'))['profiles']
  self.parks=pd.DataFrame([dict(park_code=c,park_name=p.get('park_name',c)) for c,p in self.profiles.items()])
  self.prefs=dict(temperature=[15,24],weather=65,crowds=35,minimum_years=3,years=[2005,2025])
 def test_exact_climbing_question(self):
  p=activity_fallback(Q,self.parks);e=retrieve(p,self.parks,self.prefs,self.profiles,None);t=fact_text(e)
  self.assertGreaterEqual(e['matched_park_count'],3)
  for name in ['Arches National Park','Black Canyon','Canyonlands National Park','https://www.nps.gov/arch/planyourvisit/rockclimbing.htm']:self.assertIn(name,t)
  self.assertNotIn('I can compare',t)
 def test_four_activities(self):
  for a in ['climbing','hiking','camping','kayaking']:
   p=activity_fallback('Which parks are good for '+a+'?',self.parks)
   self.assertTrue(retrieve(p,self.parks,self.prefs,self.profiles,None)['rows'])
 def test_previous_selection_cannot_limit_discovery(self):
  p=dict(intent='unsupported',park_codes=['ZION'],months=[],difficulty='Any',temperature_c=None)
  p=enforce_named_park_scope(p,Q,self.parks,dict(intent='park_info'))
  self.assertEqual(p['park_codes'],[]);self.assertEqual(p['intent'],'activities')
 def test_named_scope_and_route_intent(self):
  self.assertEqual(activity_fallback('Does Zion have climbing activities?',self.parks)['park_codes'],['ZION'])
  self.assertIsNone(activity_fallback('What moderate hikes can I do in Zion?',self.parks))
  self.assertIsNone(activity_fallback('What moderate hikes can I do in Zion?',self.parks,{'intent':'activities'}))
 def test_water_category_is_not_kayaking(self):
  p=pd.DataFrame([dict(park_code='TEST',park_name='Example')])
  rows,_=matching_parks(p,{'TEST':{'activities':[dict(name='Water activities',source_label='Swimming',url='https://www.nps.gov/test/swimming.htm')]}},['Kayaking'],[])
  self.assertEqual(rows,[])
 def test_coverage_states(self):
  p=dict(activity_fallback(Q,self.parks),park_codes=['ACAD'])
  self.assertIn('No activity data available',fact_text(retrieve(p,self.parks,self.prefs,{},None)))
  self.assertIn('No verified matching activity listings',fact_text(retrieve(p,self.parks,self.prefs,self.profiles,None)))
 def test_monthly_comparison(self):
  p=activity_fallback('Which parks have climbing activities in October?',self.parks)
  h=pd.DataFrame([(c,y,m,18,10,0,100) for c in self.parks.park_code for y in range(2020,2024) for m in range(1,13)],columns=COLUMNS['weather']+['recreation_visits'])
  with patch('src.assistant.historical_rows',return_value=h) as get:e=retrieve(p,self.parks,self.prefs,self.profiles,None,dsn='private')
  get.assert_called_once_with('private',2005,2025)
  self.assertEqual(e['rows'][0]['historical']['month'],10)
  self.assertEqual(e['historical_status'],'live_supabase')
 def test_history_failure_keeps_activity_evidence(self):
  p=activity_fallback('Where can I go climbing in October?',self.parks)
  with patch('src.assistant.historical_rows',side_effect=RuntimeError('private')):e=retrieve(p,self.parks,self.prefs,self.profiles,None,dsn='private')
  self.assertTrue(e['rows']);self.assertIn('Historical comparison unavailable',fact_text(e))
 def test_mocked_model_unsupported_is_guarded_not_claimed_live(self):
  client=Mock();p=dict(intent='unsupported',park_codes=['ZION'],months=[],difficulty='Any',temperature_c=None,activities=[])
  client.post.return_value.json.return_value={'id':'resp_mock','status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(p)}]}],'usage':{}}
  p,u=interpret(Q,self.parks,None,self.prefs,'test-key',session=client)
  self.assertEqual(p['intent'],'activities');self.assertEqual(p['park_codes'],[]);self.assertFalse(u['real_api_call_verified'])
 def test_invalid_activity(self):
  p=activity_fallback(Q,self.parks)
  with self.assertRaises(ValueError):validate_plan(dict(p,activities=['invented']),set(self.parks.park_code))
if __name__=='__main__':unittest.main()
