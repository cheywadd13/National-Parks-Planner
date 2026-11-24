"""Optional Streamlit conversation view with evidence and API usage visibility."""

import json
from hashlib import sha256
import streamlit as st
from .assistant import (interpret, retrieve, fact_text, DEFAULT_MODEL, FALLBACK_MODEL,
                        MODEL_PRICES, MAX_OUTPUT_TOKENS, check_model_access, AssistantUnavailable, activity_fallback)
from .park_profiles import profile_catalog, current_profile, current_alerts
from .conversation import general_evidence, grounded_answer, plain_fallback, contextual_fallback, ANSWER_TOKENS, evidence_documents


def render_assistant(parks, history, dsn, preferences, api_key, nps_key, model=None):
    st.header("Your parks travel assistant")
    st.caption("Ask naturally. The assistant retrieves verified park information and historical statistics, then explains the evidence conversationally. Source facts and API receipts remain inspectable. No generated SQL.")
    st.markdown("Try: **Where is a good national park that has climbing activities?** · **Which parks have the fewest visits in October?** · **What moderate hikes can I do in Zion?** · **Compare September and July in Yellowstone.**")
    model_options = list(MODEL_PRICES)
    if model and model not in model_options:
        model_options.append(model)
    selected_model = st.selectbox("Assistant model", model_options,
                                  index=model_options.index(model or DEFAULT_MODEL),
                                  help="Standard processing only. No automatic model fallback; synthesis retries once only for explicit temporary errors.")
    model = selected_model
    st.caption(f"Model: {model} · Standard processing · reasoning off for supported Luna models · {MAX_OUTPUT_TOKENS} interpretation tokens / {ANSWER_TOKENS} explanation tokens maximum · up to two calls per question: interpretation and a sourced explanation. One retry only for explicit temporary synthesis errors; no timeout retry.")
    state = st.session_state
    state.setdefault("travel_chat", [])
    state.setdefault("travel_plan", None)
    state.setdefault("travel_calls", 0)
    if st.button("Start a new conversation"):
        for key in ["travel_chat", "travel_plan", "travel_calls", "travel_temperature", "travel_references"]:
            state.pop(key, None)
        st.rerun()
    if "travel_temperature" in state:
        preferences = {**preferences, "temperature": state["travel_temperature"]}
    st.caption(f"Preferences: {preferences['temperature'][0]:g}–{preferences['temperature'][1]:g} °C · years {preferences['years'][0]}–{preferences['years'][1]} · weather/crowds {preferences['weather']}/{preferences['crowds']}. Follow-ups retain the previous interpreted park/month selection.")
    def remember_key():
        value=state.get("temporary_openai_key", "").strip()
        if value:state["_travel_api_key"]=value
        else:state.pop("_travel_api_key",None)
    def forget_key():
        for key in ["temporary_openai_key","_travel_api_key","model_access_result"]:state.pop(key,None)
    with st.expander("API setup, cost and privacy"):
        st.markdown("Configure `OPENAI_API_KEY` in Streamlit secrets or the server environment. Optional `OPENAI_MODEL` overrides the default. Never paste a key into chat. Questions, park names and preferences are sent to OpenAI; database credentials are never sent. Requests use `store=false`; this does not override provider retention policies.")
        st.markdown("Uses GPT-6 Luna with Standard processing. Each question uses up to two bounded requests: interpretation and a sourced explanation. Synthesis can retry once after an explicit temporary HTTP error; timeouts are not retried automatically. No automatic model fallback. Actual costs depend on tokens and provider rates; set account billing limits separately. [Provider pricing](https://developers.openai.com/api/docs/models/gpt-6-luna)")
        if not api_key:
            state.setdefault("temporary_openai_key",state.get("_travel_api_key", ""))
            api_key = st.text_input("OpenAI API key (this session only)", type="password",
                                    key="temporary_openai_key", on_change=remember_key,
                                    help="Optional alternative to server configuration. Sent only to OpenAI over HTTPS; not written to a file or included in prompts. Clear it when finished.")
            remember_key()
            api_key=api_key or state.get("_travel_api_key")
            st.button("Forget session API key", on_click=forget_key)
        if api_key:
            check_identity = sha256((api_key + model).encode()).hexdigest()
            if st.button("Check model access (no generated tokens)"):
                state["model_access_result"] = (check_identity, check_model_access(api_key, model))
            prior_check = state.get("model_access_result")
            if prior_check and prior_check[0] == check_identity:
                st.info(prior_check[1]["message"])
    if not api_key:
        st.info("The assistant is ready to configure. Open API setup, cost and privacy to enter a key for this session, or configure OPENAI_API_KEY on the server. Verified activity-discovery questions work through a clearly labeled deterministic fallback without a key. Other park guides, charts and recommendations remain available.")
    if not dsn:
        st.warning("Historical assistant recommendations require live Supabase mode. Official park and trail questions remain available; incomplete CSV exports are not used for assistant statistics.")
    for message in state["travel_chat"]:
        with st.chat_message(message["role"]):
            st.markdown(message["text"])
            if message.get("evidence"):
                previous_usage = message["evidence"].get("usage", {})
                if previous_usage.get("real_api_call_verified"):
                    st.caption(f"Verified OpenAI interpretation · {previous_usage['response_id']} · retrieved facts and answer provenance available below.")
                elif previous_usage.get("interpretation_source", "").startswith("Deterministic"):
                    st.caption("Deterministic activity fallback — no successful live LLM call. Facts come from reviewed official NPS records.")
                answer_receipt=message["evidence"].get("answer_usage")
                if answer_receipt and answer_receipt.get("real_api_call_verified"):
                    st.caption(f"Live evidence-grounded explanation · {answer_receipt['response_id']}")
                with st.expander("Retrieved evidence & interpreted query"):
                    st.json(message["evidence"])
    question = st.chat_input("Ask about park activities, hikes, historical weather or crowds…", max_chars=1000)
    if not question:
        return
    if state["travel_calls"] >= 20:
        st.warning("This conversation has reached its 20-call limit. Start a new conversation to continue. This is a session guard, not an account-wide spending cap.")
        return
    state["travel_chat"].append({"role": "user", "text": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        try:
            with st.spinner("Interpreting your question and checking evidence…"):
                local_plan = activity_fallback(question, parks, state["travel_plan"]) or contextual_fallback(question, parks, state["travel_plan"], preferences)
                try:
                    if api_key:
                        state["travel_calls"] += 1
                    plan, usage = interpret(question, parks, state["travel_plan"], preferences, api_key, model or DEFAULT_MODEL,
                                            evidence_refs=state.get("travel_references", []))
                except AssistantUnavailable as interpretation_error:
                    if local_plan is None:
                        raise
                    plan = local_plan
                    usage = {"real_api_call_verified": False, "interpretation_source": "Deterministic activity fallback" if plan["intent"] == "activities" else "Deterministic evidence fallback", "reason": str(interpretation_error)}
                if usage.get("real_api_call_verified"):
                    usage["interpretation_source"] = "Live OpenAI API interpretation with validated activity-scope guard"
                elif "interpretation_source" not in usage:
                    usage["interpretation_source"] = "Unverified or test-provider interpretation"
                state["travel_plan"] = plan
                if plan["temperature_c"] is not None:
                    state["travel_temperature"] = plan["temperature_c"]
                st.caption(f"Interpreted request: {plan['intent']} · parks {', '.join(plan['park_codes']) or 'all'} · months {', '.join(map(str, plan['months'])) or 'any'} · difficulty {plan['difficulty']}. Discovery-map activity/state filters do not silently exclude assistant records.")
                profiles = dict(profile_catalog())
                if plan["intent"] == "park_info":
                    for code in plan["park_codes"]:
                        profiles[code] = current_profile(code, nps_key)[0]
                if plan["intent"] == "general":
                    evidence=general_evidence(plan, question, parks, preferences, profiles, lambda c: current_alerts(c,nps_key),dsn)
                elif not dsn and plan["intent"] in ["quiet_parks", "mild_weather", "best_months", "compare_months", "visit_and_hikes"]:
                    unavailable = {"kind": "clarify", "rows": [], "message": "Connect live Supabase to answer historical recommendation questions. Incomplete CSV exports are not used by this assistant for statistics."}
                    if plan["intent"] == "visit_and_hikes":
                        trails = retrieve({**plan, "intent": "hikes"}, parks, preferences, profiles, lambda c: current_alerts(c, nps_key))
                        evidence = {"kind": "visit_and_hikes", "historical": unavailable, "trails": trails, "rows": trails["rows"]}
                    else:
                        evidence = unavailable
                else:
                    evidence = retrieve(plan, parks, preferences, profiles, lambda c: current_alerts(c, nps_key), dsn, history)
                state["travel_references"] = [{key: row[key] for key in ["park_code", "month", "name", "trail_id"] if key in row}
                                               for row in evidence["rows"][:3]]
                text = plain_fallback(evidence)
                answer_usage=None
                answer_error=None
                if api_key and usage.get("real_api_call_verified") and state["travel_calls"] < 20:
                    try:
                        state["travel_calls"] += 1
                        text,answer_usage=grounded_answer(question,evidence,api_key,model or DEFAULT_MODEL,state["travel_chat"][:-1])
                    except AssistantUnavailable as error:
                        answer_error=str(error)
                packet = json.loads(json.dumps({"plan": plan, "evidence": evidence, "usage": usage, "answer_usage": answer_usage, "answer_error": answer_error, "citation_documents": evidence_documents(evidence)}, default=str))
                state["travel_chat"].append({"role": "assistant", "text": text, "evidence": packet})
                state["travel_chat"] = state["travel_chat"][-16:]
                st.markdown(text)
                if answer_usage and answer_usage.get("real_api_call_verified"):
                    st.success(f"Live evidence-grounded explanation verified · {answer_usage['response_id']} · {answer_usage['model']}.")
                elif answer_error:
                    st.info(answer_error+" Showing application-rendered verified facts, not an LLM-written answer.")
                if usage.get("real_api_call_verified"):
                    st.success(f"Real OpenAI API interpretation verified · {usage['response_id']} · {usage['model']}. Question interpretation verified. The evidence panel separately identifies conversational synthesis or application-rendered fallback.")
                if usage.get("interpretation_source", "").startswith("Deterministic"):
                    st.info(usage["interpretation_source"]+" — no successful live LLM call. "+usage.get("reason", "")+" Recommendations above come from reviewed official NPS records.")
                with st.expander("Retrieved evidence & interpreted query"):
                    st.json(packet)
        except AssistantUnavailable as error:
            st.warning(str(error))
        except Exception:
            st.warning("Verified data retrieval failed. No factual answer was generated. Check the data connection and try again.")
