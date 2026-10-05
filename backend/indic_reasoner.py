"""
Indic Agricultural Reasoning Engine for KisanSetu
Performs semantic intent routing and extracts answers for:
1. Mandi Commodity Prices (APMC)
2. Crop Doctor / Pest & Disease Diagnosis
3. Government Schemes & Subsidies (PM-Kisan, Fasal Bima, KCC)
"""

import os
import json
import logging
from typing import Dict, Any, Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class IndicReasoner:
    def __init__(self):
        self.mandi_data = self._load_json("mandi_rates.json")
        self.crop_data = self._load_json("crop_advisory.json")
        self.scheme_data = self._load_json("govt_schemes.json")

    def _load_json(self, filename: str) -> Dict[str, Any]:
        path = os.path.join(DATA_DIR, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def process_query(self, transcript: str, language_code: str = "hi-IN") -> Dict[str, Any]:
        """
        Process user query transcript and return structured reasoning outcome:
        - intent: 'crop_health' | 'mandi' | 'scheme' | 'general'
        - voice_response: text specifically crafted for Indic voice synthesis
        - display_card: rich UI data
        """
        t_lower = transcript.lower().strip()
        if not t_lower:
            return self._fallback_greeting(language_code)

        # 1. Prioritize Crop Health & Rog Nidan
        crop_res = self._check_crop(t_lower, language_code)
        if crop_res:
            return crop_res

        # 2. Prioritize Schemes
        scheme_res = self._check_scheme(t_lower, language_code)
        if scheme_res:
            return scheme_res

        # 3. Check Mandi Price Queries (ONLY if price/market intent exists!)
        mandi_res = self._check_mandi(t_lower, language_code)
        if mandi_res:
            return mandi_res

        # 4. Fallback / General Farmer Advisory
        return self._general_agri_response(t_lower, language_code)

    def _check_crop(self, text: str, lang: str) -> Optional[Dict[str, Any]]:
        diseases = self.crop_data.get("diseases", [])
        
        # General crop disease indicator keywords
        general_health_words = [
            "पत्ते", "पीले", "पीला", "मुड़", "रोग", "कीड़े", "कीड़ा", "सुंडी", "धब्बे", 
            "बीमारी", "दवा", "इलाज", "उपाय", "छिड़काव", "सूख", "खराब", "मर रहे", 
            "leaf", "yellow", "curl", "disease", "pest", "spray", "remedy", "cure"
        ]
        has_health_intent = any(hw in text for hw in general_health_words)

        for d in diseases:
            crop_aliases = d.get("crop_aliases", [])
            symptom_triggers = d.get("symptom_triggers", [])

            # Check if this specific crop is mentioned
            crop_matched = any(ca.lower() in text for ca in crop_aliases)
            # Check if any symptom of this disease is mentioned
            symptom_matched = any(st.lower() in text for st in symptom_triggers)

            # Match if (crop is mentioned and symptom/health is mentioned) OR (direct symptom match)
            if (crop_matched and (symptom_matched or has_health_intent)) or (crop_matched and "रोग" in text):
                crop_name = d.get("crop")
                symptom = d.get("symptom")
                organic = d.get("organic_remedy")
                chemical = d.get("chemical_remedy")

                if "mr" in lang:
                    voice_text = (
                        f"शेतकरी बंधू, हे लक्षण {crop_name} च्या रोगाचे आहे. "
                        f"जैविक उपाय: {organic[:85]} "
                        f"अधिक प्रादुर्भाव असल्यास {chemical[:80]} फवारणी करा."
                    )
                elif "te" in lang:
                    voice_text = (
                        f"రైతు మిత్రమా, ఇది {crop_name} తెగులు లక్షణం. "
                        f"సేంద్రీయ నివారణ: {organic[:85]}."
                    )
                else:
                    voice_text = (
                        f"किसान भाई, यह {crop_name} में रोग के लक्षण हैं। "
                        f"जैविक उपचार के लिए: {organic[:90]} "
                        f"अधिक प्रकोप होने पर {chemical[:85]} का छिड़काव करें।"
                    )

                return {
                    "intent": "crop_health",
                    "title": f"Crop Doctor: {crop_name}",
                    "voice_response": voice_text,
                    "data": {
                        "crop": crop_name,
                        "symptom": symptom,
                        "organic_remedy": organic,
                        "chemical_remedy": chemical,
                        "prevention": d.get("prevention")
                    }
                }
        return None

    def _check_mandi(self, text: str, lang: str) -> Optional[Dict[str, Any]]:
        # MANDI GUARD: Must contain price/market words!
        price_keywords = [
            "bhav", "भाव", "दर", "रेट", "rate", "price", "mandi", "मंडी", 
            "बाजार", "मार्केट", "मार्केटमध्ये", "बिक्री", "क्विंटल", "ధర", "దర", "ಬೆಲೆ"
        ]
        has_price_intent = any(k in text for k in price_keywords)

        commodities = self.mandi_data.get("commodities", {})
        matched_comm = None
        matched_key = None

        for key, info in commodities.items():
            for alias in info.get("names", []):
                if alias.lower() in text:
                    matched_comm = info
                    matched_key = key
                    break
            if matched_comm:
                break

        # ONLY return Mandi data if user actually asked about price or market!
        if matched_comm and has_price_intent:
            markets = matched_comm.get("markets", [])
            primary_mkt = markets[0] if markets else {}
            comm_title = matched_key.capitalize()

            if "mr" in lang:
                voice_text = (
                    f"शेतकरी बंधू, {primary_mkt.get('mandi')} मार्केटमध्ये {comm_title} चा सरासरी भाव "
                    f"{primary_mkt.get('modal_price')} रुपये प्रति क्विंटल चालू आहे. "
                    f"कमाल भाव {primary_mkt.get('max_price')} रुपयांपर्यंत पोहोचला आहे."
                )
            elif "te" in lang:
                voice_text = (
                    f"రైతు మిత్రమా, {primary_mkt.get('mandi')} మార్కెట్‌లో {comm_title} సగటు ధర "
                    f"క్వింటాల్‌కు {primary_mkt.get('modal_price')} రూపాయలు పలుకుతోంది."
                )
            else:
                voice_text = (
                    f"राम राम किसान भाई! {primary_mkt.get('mandi')} मंडी में {comm_title} का मॉडल भाव "
                    f"{primary_mkt.get('modal_price')} रुपये प्रति क्विंटल है, और अधिकतम भाव "
                    f"{primary_mkt.get('max_price')} रुपये तक पहुंचा है।"
                )

            return {
                "intent": "mandi",
                "title": f"Mandi Rates: {comm_title}",
                "voice_response": voice_text,
                "data": {
                    "commodity": comm_title,
                    "market": primary_mkt.get("mandi"),
                    "modal_price": primary_mkt.get("modal_price"),
                    "min_price": primary_mkt.get("min_price"),
                    "max_price": primary_mkt.get("max_price"),
                    "unit": matched_comm.get("unit"),
                    "trend": primary_mkt.get("trend")
                }
            }
        elif has_price_intent:
            voice_text = (
                "किसान भाई, नासिक मंडी में प्याज 2400 रुपये और खन्ना मंडी में गेहूं 2350 रुपये प्रति क्विंटल चल रहा है। "
                "आप किसी खास फसल का भाव पूछना चाहते हैं?"
            )
            return {
                "intent": "mandi",
                "title": "Mandi Overview",
                "voice_response": voice_text,
                "data": {"overview": "Onion: ₹2400/Q, Wheat: ₹2350/Q, Cotton: ₹7450/Q"}
            }

        return None

    def _check_scheme(self, text: str, lang: str) -> Optional[Dict[str, Any]]:
        schemes = self.scheme_data.get("schemes", [])
        for s in schemes:
            for kw in s.get("keywords", []):
                if kw.lower() in text or kw in text:
                    voice_text = (
                        f"किसान भाई, {s.get('name')} के तहत: {s.get('benefit')[:110]} "
                        f"अधिक जानकारी या सहायता के लिए हेल्पलाइन {s.get('helpline')} पर संपर्क करें।"
                    )
                    return {
                        "intent": "scheme",
                        "title": s.get("name"),
                        "voice_response": voice_text,
                        "data": {
                            "name": s.get("name"),
                            "benefit": s.get("benefit"),
                            "eligibility": s.get("eligibility"),
                            "how_to_avail": s.get("how_to_avail"),
                            "helpline": s.get("helpline")
                        }
                    }

        # Check broad/generic scheme inquiry
        generic_scheme_words = ["योजना", "योजनाएं", "scheme", "yojana", "yojna", "सरकारी", "subsidy", "सब्सिडी"]
        if any(gw in text for gw in generic_scheme_words):
            voice_text = (
                "किसान भाई, प्रमुख सरकारी योजनाओं में: पीएम किसान सम्मान निधि से प्रति वर्ष 6000 रुपये सहायता, "
                "फसल बीमा योजना से नुकसान पर क्षतिपूर्ति, और किसान क्रेडिट कार्ड से मात्र 4 प्रतिशत ब्याज पर ऋण मिलता है।"
            )
            return {
                "intent": "scheme",
                "title": "Major Government Schemes (मुख्य सरकारी योजनाएं)",
                "voice_response": voice_text,
                "data": {
                    "name": "PM Kisan, PM Fasal Bima & KCC",
                    "benefit": "1. PM Kisan: ₹6000 वार्षिक सहायता DBT द्वारा | 2. Fasal Bima: प्राकृतिक आपदा पर क्षतिपूर्ति | 3. KCC: मात्र 4% ब्याज पर ₹3 लाख तक ऋण।",
                    "eligibility": "सभी भूमिधारक एवं काश्तकार किसान परिवार।",
                    "how_to_avail": "निकटतम CSC सेंटर, बैंक शाखा या pmkisan.gov.in / pmfby.gov.in पोर्टल पर आवेदन करें।",
                    "helpline": "155261 / 1800-180-1551 (Kisan Call Centre)"
                }
            }

        return None

    def _general_agri_response(self, text: str, lang: str) -> Dict[str, Any]:
        voice_text = (
            "राम राम किसान भाई! मैं किसान सेतु हूँ। आप मुझसे मंडी भाव, फसल में लगने वाले कीड़े या बीमारी, "
            "या सरकारी योजनाओं के बारे में अपनी भाषा में पूछ सकते हैं।"
        )
        return {
            "intent": "general",
            "title": "KisanSetu Advisory",
            "voice_response": voice_text,
            "data": {
                "sample_questions": [
                    "नासिक मंडी में प्याज का क्या भाव है?",
                    "टमाटर के पत्ते पीले पड़ रहे हैं क्या करें?",
                    "पीएम किसान सम्मान निधि की किस्त कब आएगी?",
                    "कपास में गुलाबी सुंडी का इलाज बताएं"
                ]
            }
        }

    def _fallback_greeting(self, lang: str) -> Dict[str, Any]:
        return self._general_agri_response("", lang)
