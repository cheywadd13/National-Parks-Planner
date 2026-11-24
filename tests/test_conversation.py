import json,unittest
from unittest.mock import Mock,patch
import requests
import pandas as pd
from src.conversation import grounded_answer,general_evidence,contextual_fallback,plain_fallback
from src.assistant import AssistantUnavailable,interpret

def client_with(text,sources=None):
 c=Mock();c.post.return_value.status_code=200
 c.post.return_value.json.return_value={'status':'completed','id':'resp_test','model':'gpt-6-luna','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps({'sections':[{'text':text,'sources':['E1'] if sources is None else sources}]})}]}],'usage':{'input_tokens':100,'output_tokens':40}}
 return c
class ConversationTests(unittest.TestCase):
 def setUp(self):
  self.e={'kind':'clarify','rows':[],'message':'Verified Arches climbing guide, 21 paired years. https://www.nps.gov/arch/planyourvisit/rockclimbing.htm'}
 def test_grounded_natural_reply(self):
  c=client_with('Arches is an option because its official guide lists climbing.')
  text,u=grounded_answer('Where can I climb?',self.e,'test-key',session=c)
  self.assertIn('[E1]',text);self.assertIn('https://www.nps.gov/arch/',text)
  self.assertFalse(u['real_api_call_verified'])
  payload=c.post.call_args.kwargs['json'];self.assertNotIn('test-key',json.dumps(payload));self.assertEqual(payload['max_output_tokens'],650)
 def test_no_arbitrary_source_or_url(self):
  for c in [client_with('Arches climbing',['E99']),client_with('Visit https://evil.test')]:
   with self.assertRaises(AssistantUnavailable):grounded_answer('Where?',self.e,'key',session=c)
 def test_new_visitor_counts_rejected(self):
  with self.assertRaises(AssistantUnavailable):grounded_answer('How many visits?',self.e,'key',session=client_with('Arches has 999999 visitors.'))
 def test_equivalent_numeric_formats_are_allowed(self):
  e={'kind':'clarify','rows':[],'message':'Evidence: 100.0 visits and 1,243 observations.'}
  text,_=grounded_answer('How many?',e,'key',session=client_with('The evidence shows 100 visits and 1243 observations.'))
  self.assertIn('100 visits',text)
 def test_timeout_not_retried(self):
  c=Mock();c.post.side_effect=requests.Timeout()
  with self.assertRaises(AssistantUnavailable):grounded_answer('Where?',self.e,'key',session=c)
  self.assertEqual(c.post.call_count,1)
 def test_explicit_temporary_error_retried_once(self):
  c=client_with('Arches lists climbing.');bad=Mock(status_code=503)
  c.post.side_effect=[bad,c.post.return_value]
  _,u=grounded_answer('Where?',self.e,'key',session=c)
  self.assertEqual(c.post.call_count,2);self.assertEqual(u['attempts'],2)
 def test_missing_key(self):
  with self.assertRaises(AssistantUnavailable):grounded_answer('Where?',self.e,None)
 def test_factual_section_needs_citation(self):
  with self.assertRaises(AssistantUnavailable):grounded_answer('Where?',self.e,'key',session=client_with('Arches offers climbing.',[]))
 def test_conversation_context_is_bounded(self):
  c=client_with('Which park interests you?',[])
  grounded_answer('What about that one?',self.e,'key',conversation=[{'role':'user','text':'a'*2000}]*20,session=c)
  ctx=json.loads(c.post.call_args.kwargs['json']['input']);self.assertEqual(len(ctx['recent_conversation']),6);self.assertEqual(len(ctx['recent_conversation'][0]['text']),900)
 def test_best_hike_unknown_coverage_gets_specific_sources(self):
  parks=pd.DataFrame([{'park_code':'GRTE','park_name':'Grand Teton National Park'}]);prefs={'selected_park':'GRTE','years':[2005,2025]}
  plan=contextual_fallback('What is the best hike in Grand Teton?',parks,None,prefs)
  self.assertEqual(plan['park_codes'],['GRTE'])
  e=general_evidence(plan,'What hike?',parks,prefs,{'GRTE':{'description':'Official description','activities':[],'official_url':'https://www.nps.gov/grte/index.htm'}},None)
  t=plain_fallback(e);self.assertIn('No trail data available',t);self.assertIn('Official description',t)
 def test_right_now_uses_seasonal_month_not_current_weather(self):
  parks=pd.DataFrame([{'park_code':'ZION','park_name':'Zion National Park'}])
  p=contextual_fallback('Which park should I visit right now?',parks,None,{'selected_park':'ZION'})
  self.assertEqual(len(p['months']),1);self.assertTrue(1<=p['months'][0]<=12)
 def test_unsupported_park_query_is_retrieved(self):
  parks=pd.DataFrame([{'park_code':'GRTE','park_name':'Grand Teton National Park'}]);c=Mock();c.post.return_value.json.return_value={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(dict(intent='unsupported',park_codes=[],months=[],difficulty='Any',temperature_c=None,activities=[]))}]}]}
  p,_=interpret('What is the best hike in Grand Teton?',parks,None,{'selected_park':'GRTE'},'key',session=c)
  self.assertEqual(p['intent'],'general')
if __name__=='__main__':unittest.main()
