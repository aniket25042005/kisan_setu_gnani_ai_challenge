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
                elif "kn" in lang:
                    voice_text = (
                        f"ರೈತ ಮಿತ್ರರೇ, ಇದು {crop_name} ಬೆಳೆಯಲ್ಲಿ ರೋಗದ ಲಕ್ಷಣವಾಗಿದೆ. "
                        f"ಸಾವಯವ ಪರಿಹಾರ: {organic[:85]}."
                    )
                elif "ta" in lang:
                    voice_text = (
                        f"விவசாய நண்பரே, இது {crop_name} பயிரின் நோய் அறிகுறி. "
                        f"இயற்கை நிவாரணம்: {organic[:85]}."
                    )
                elif "en" in lang:
                    voice_text = (
                        f"Dear farmer, these symptoms indicate {crop_name} disease. "
                        f"Organic remedy: {organic[:85]} "
                        f"For severe infestation, spray {chemical[:80]}."
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

    @staticmethod
    def _normalize_indic(s: str) -> str:
        """Normalize Indic text variants (Chandrabindu, Anusvara, Nukta)."""
        if not s:
            return ""
        # Replace Chandrabindu (ँ U+0901) with Anusvara (ं U+0902)
        s = s.replace('\u0901', '\u0902')
        # Remove Nukta (़ U+093C) so ज़ -> ज, फ़ -> फ
        s = s.replace('\u093c', '')
        return s.lower().strip()

    def _find_market(self, markets: list, text: str, norm_text: str) -> dict:
        """Find user-specified market by city or state name, or default to primary market."""
        if not markets:
            return {}
        city_keywords = {
            "nashik": ["nashik", "lasalgaon", "नासिक", "नाशिक", "लासलगाव"],
            "indore": ["indore", "इंदौर", "इंदूर"],
            "khanna": ["khanna", "खन्ना"],
            "karnal": ["karnal", "करनाल"],
            "azadpur": ["azadpur", "आजादपुर", "दिल्ली", "delhi"],
            "kolar": ["kolar", "कोलार"],
            "madanapalle": ["madanapalle", "मदनापल्ले"],
            "rajkot": ["rajkot", "राजकोट"],
            "warangal": ["warangal", "वारंगल"],
            "amravati": ["amravati", "अमरावती"],
            "latur": ["latur", "लातूर"]
        }
        for mkt in markets:
            mkt_name_lower = mkt.get("mandi", "").lower()
            for city_key, aliases in city_keywords.items():
                if any(alias in text or alias in norm_text for alias in aliases):
                    if city_key in mkt_name_lower or any(a in mkt_name_lower for a in aliases):
                        return mkt
        return markets[0]

    def _check_mandi(self, text: str, lang: str) -> Optional[Dict[str, Any]]:
        # MANDI GUARD: Must contain price/market words!
        price_keywords = [
            "bhav", "भाव", "दर", "रेट", "rate", "price", "mandi", "मंडी", 
            "बाजार", "मार्केट", "मार्केटमध्ये", "बिक्री", "क्विंटल", "ధర", "దర", "ಬೆಲೆ", "விலை",
            "दाम", "dam", "cost", "rupee", "rupees", "रुपये"
        ]
        has_price_intent = any(k in text for k in price_keywords)
        norm_text = self._normalize_indic(text)

        commodities = self.mandi_data.get("commodities", {})
        matched_items = []

        for key, info in commodities.items():
            for alias in info.get("names", []):
                if alias.lower() in text or self._normalize_indic(alias) in norm_text:
                    matched_items.append((key, info))
                    break

        # ONLY return Mandi data if user actually asked about price or market!
        if matched_items and has_price_intent:
            if len(matched_items) == 1:
                # Exactly one commodity requested (e.g. ONLY wheat, or ONLY onion)
                key, info = matched_items[0]
                comm_title = key.capitalize()
                primary_mkt = self._find_market(info.get("markets", []), text, norm_text)

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
                elif "kn" in lang:
                    voice_text = (
                        f"ರೈತ ಮಿತ್ರರೇ, {primary_mkt.get('mandi')} ಮಾರುಕಟ್ಟೆಯಲ್ಲಿ {comm_title} ಸರಾಸರಿ ಬೆಲೆ "
                        f"ಕ್ವಿಂಟಾಲ್‌ಗೆ {primary_mkt.get('modal_price')} ರೂಪಾಯಿ ಇದೆ."
                    )
                elif "ta" in lang:
                    voice_text = (
                        f"விவசாய நண்பரே, {primary_mkt.get('mandi')} சந்தையில் {comm_title} சராசரி விலை "
                        f"குவிண்டாலுக்கு {primary_mkt.get('modal_price')} ரூபாய் ஆக உள்ளது."
                    )
                elif "en" in lang:
                    voice_text = (
                        f"Farmer friend, in {primary_mkt.get('mandi')} market the modal price of {comm_title} "
                        f"is {primary_mkt.get('modal_price')} rupees per quintal, with maximum price of "
                        f"{primary_mkt.get('max_price')} rupees."
                    )
                else:
                    # Hindi
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
                        "unit": info.get("unit"),
                        "trend": primary_mkt.get("trend")
                    }
                }
            else:
                # Multiple commodities requested (e.g. Onion AND Wheat together)
                details = []
                for k, info in matched_items:
                    mkt = self._find_market(info.get("markets", []), text, norm_text)
                    details.append({
                        "commodity": k.capitalize(),
                        "market": mkt.get("mandi"),
                        "modal_price": mkt.get("modal_price"),
                        "max_price": mkt.get("max_price")
                    })

                comm_names_hi = " और ".join([d["commodity"] for d in details])
                parts_hi = [f"{d['market']} मंडी में {d['commodity']} का भाव {d['modal_price']} रुपये" for d in details]
                parts_en = [f"in {d['market']} {d['commodity']} is {d['modal_price']} rupees" for d in details]
                parts_mr = [f"{d['market']} मार्केटमध्ये {d['commodity']} {d['modal_price']} रुपये" for d in details]

                if "mr" in lang:
                    voice_text = f"शेतकरी बंधू, {', आणि '.join(parts_mr)} प्रति क्विंटल चालू आहे."
                elif "en" in lang:
                    voice_text = f"Farmer friend, {', and '.join(parts_en)} per quintal."
                else:
                    voice_text = f"राम राम किसान भाई! {', और '.join(parts_hi)} प्रति क्विंटल चल रहा है।"

                primary_mkt = details[0]
                return {
                    "intent": "mandi",
                    "title": f"Mandi Rates: {comm_names_hi}",
                    "voice_response": voice_text,
                    "data": {
                        "commodity": comm_names_hi,
                        "market": primary_mkt["market"],
                        "modal_price": primary_mkt["modal_price"],
                        "min_price": primary_mkt["modal_price"],
                        "max_price": primary_mkt["max_price"],
                        "unit": "₹ / क्विंटल",
                        "trend": "stable",
                        "multi_items": details
                    }
                }

        elif has_price_intent:
            if "mr" in lang:
                voice_text = (
                    "शेतकरी बंधू, आपण कोणत्या विशिष्ट पिकाचा भाव विचारत आहात? जसे कांदा, गहू, टोमॅटो, किंवा कापूस."
                )
            elif "te" in lang:
                voice_text = (
                    "రైతు మిత్రమా, మీరు ఏ నిర్దిష్ట పంట ధర తెలుసుకోవాలనుకుంటున్నారు? ఉదాహరణకు ఉల్లిపాయ, గోధుమలు, లేదా పత్తి."
                )
            elif "kn" in lang:
                voice_text = (
                    "ರೈತ ಮಿತ್ರರೇ, ನೀವು ಯಾವ ನಿರ್ದಿಷ್ಟ ಬೆಳೆಯ ಬೆಲೆಯನ್ನು ತಿಳಿಯಲು ಬಯಸುತ್ತೀರಿ? ಉದಾಹರಣೆಗೆ ಈರುಳ್ಳಿ, ಗೋಧಿ, ಅಥವಾ ಹತ್ತಿ."
                )
            elif "ta" in lang:
                voice_text = (
                    "விவசாய நண்பரே, எந்த பயிரின் சந்தை விலையை அறிய விரும்புகிறீர்கள்? எ.கா. வெங்காயம், கோதுமை, அல்லது பருத்தி."
                )
            elif "en" in lang:
                voice_text = (
                    "Farmer friend, which specific crop price would you like to check? For example: onion, wheat, tomato, or cotton."
                )
            else:
                voice_text = (
                    "किसान भाई, आप किस फसल का मंडी भाव जानना चाहते हैं? जैसे प्याज, गेहूं, टमाटर, कपास या सोयाबीन।"
                )
            return {
                "intent": "mandi",
                "title": "Mandi Rate Inquiry",
                "voice_response": voice_text,
                "data": {"overview": "Onion, Wheat, Tomato, Cotton, Soybean available"}
            }

        return None

    def _check_scheme(self, text: str, lang: str) -> Optional[Dict[str, Any]]:
        schemes = self.scheme_data.get("schemes", [])
        for s in schemes:
            for kw in s.get("keywords", []):
                if kw.lower() in text or kw in text:
                    if "mr" in lang:
                        voice_text = f"शेतकरी बंधू, {s.get('name')} अंतर्गत: {s.get('benefit')[:100]} अधिक माहितीसाठी हेल्पलाइन {s.get('helpline')} वर संपर्क करा."
                    elif "te" in lang:
                        voice_text = f"రైతు మిత్రమా, {s.get('name')} పథకం ద్వారా: {s.get('benefit')[:100]} సహాయం కోసం హెల్ప్‌లైన్ {s.get('helpline')} కు కాల్ చేయండి."
                    elif "kn" in lang:
                        voice_text = f"ರೈತ ಮಿತ್ರರೇ, {s.get('name')} ಯೋಜನೆಯಡಿ: {s.get('benefit')[:100]} ಹೆಚ್ಚಿನ ಮಾಹಿತಿಗಾಗಿ ಸಹಾಯವಾಣಿ {s.get('helpline')} ಗೆ ಸಂಪರ್ಕಿಸಿ."
                    elif "ta" in lang:
                        voice_text = f"விவசாய நண்பரே, {s.get('name')} திட்டத்தின் கீழ்: {s.get('benefit')[:100]} கூடுதல் தகவலுக்கு உதவி எண் {s.get('helpline')} ஐ தொடர்பு கொள்ளவும்."
                    elif "en" in lang:
                        voice_text = (
                            f"Dear farmer, under {s.get('name')}: {s.get('benefit')[:110]} "
                            f"For more details or assistance, contact helpline {s.get('helpline')}."
                        )
                    else:
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
        generic_scheme_words = ["योजना", "योजनाएं", "scheme", "schemes", "yojana", "yojna", "सरकारी", "subsidy", "सब्सिडी", "పథకాలు", "ಯೋಜನೆ", "திட்டம்"]
        if any(gw in text for gw in generic_scheme_words):
            if "mr" in lang:
                voice_text = "शेतकरी बंधू, मुख्य सरकारी योजनांमध्ये: पीएम किसान सन्मान निधी, पीक विमा योजना, आणि किसान क्रेडिट कार्ड द्वारे कमी व्याजावर कर्ज मिळते."
            elif "te" in lang:
                voice_text = "రైతు మిత్రమా, ప్రధాన ప్రభుత్వ పథకాలలో: పీఎం కిసాన్ సమ్మాన్ నిధి, పంట బీమా పథకం, మరియు కేసీసీ ద్వారా తక్కువ వడ్డీకే రుణాలు లభిస్తాయి."
            elif "kn" in lang:
                voice_text = "ರೈತ ಮಿತ್ರರೇ, ಮುಖ್ಯ ಸರ್ಕಾರಿ ಯೋಜನೆಗಳಲ್ಲಿ: ಪಿಎಂ ಕಿಸಾನ್ ಸಮ್ಮಾನ್ ನಿಧಿ, ಬೆಳೆ ವಿಮೆ ಮತ್ತು ಕಿಸಾನ್ ಕ್ರೆಡಿಟ್ ಕಾರ್ಡ್ ಮೂಲಕ ಕಡಿಮೆ ಬಡ್ಡಿದರದಲ್ಲಿ ಸಾಲ ದೊರೆಯುತ್ತದೆ."
            elif "ta" in lang:
                voice_text = "விவசாய நண்பரே, முக்கிய அரசு திட்டங்களில்: பிஎம் கிசான் திட்டம் மூலம் நிதி உதவி, பயிர் காப்பீட்டு திட்டம் மற்றும் குறைந்த வட்டியில் கிசான் கிரெடிட் கார்டு கடன் கிடைக்கும்."
            elif "en" in lang:
                voice_text = (
                    "Dear farmer, major government schemes include: PM-Kisan Samman Nidhi with 6,000 rupees annual DBT support, "
                    "Pradhan Mantri Fasal Bima Yojana for crop loss compensation, and Kisan Credit Card offering loans at just 4% interest."
                )
            else:
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
        if "mr" in lang:
            voice_text = "नमस्कार शेतकरी बंधू! मी किसान सेतु आहे. आपण मला बाजारभाव, पिकावरील रोग किंवा सरकारी योजनांबद्दल विचारू शकता."
        elif "te" in lang:
            voice_text = "నమస్కారం రైతు మిత్రమా! నేను కిసాన్ సేతు. మీరు నన్ను మార్కెట్ ధరలు, పంట తెగుళ్లు లేదా ప్రభుత్వ పథకాల గురించి అడగవచ్చు."
        elif "kn" in lang:
            voice_text = "ನಮಸ್ಕಾರ ರೈತ ಮಿತ್ರರೇ! ನಾನು ಕಿಸಾನ್ ಸೇತು. ನೀವು ಮಾರುಕಟ್ಟೆ ಬೆಲೆ, ಬೆಳೆ ರೋಗ ಅಥವಾ ಸರ್ಕಾರದ ಯೋಜನೆಗಳ ಬಗ್ಗೆ ಕೇಳಬಹುದು."
        elif "ta" in lang:
            voice_text = "வணக்கம் விவசாய நண்பரே! நான் கிசான் சேது. நீங்கள் என்னிடம் சந்தை விலை, பயிர் நோய்கள் அல்லது அரசு திட்டங்கள் பற்றி கேட்கலாம்."
        elif "en" in lang:
            voice_text = (
                "Namaste farmer friend! I am KisanSetu. You can ask me about live APMC mandi rates, "
                "crop pest remedies and disease diagnosis, or government farmer schemes in your language."
            )
        else:
            voice_text = (
                "राम राम किसान भाई! मैं किसान सेतु हूँ। आप मुझसे मंडी भाव, फसल में लगने वाले कीड़े या बीमारी, "
                "या सरकारी योजनाओं के बारे में अपनी भाषा में पूछ सकते हैं।"
            )

        sample_questions = [
            "नासिक मंडी में प्याज का क्या भाव है?",
            "टमाटर के पत्ते पीले पड़ रहे हैं क्या करें?",
            "पीएम किसान सम्मान निधि की किस्त कब आएगी?",
            "कपास में गुलाबी सुंडी का इलाज बताएं"
        ]
        if "en" in lang:
            sample_questions = [
                "What is the onion rate in Nashik mandi today?",
                "Tomato leaves are turning yellow, what remedy should I use?",
                "When will the next PM-Kisan installment be credited?",
                "How to treat pink bollworm in cotton?"
            ]

        return {
            "intent": "general",
            "title": "KisanSetu Advisory",
            "voice_response": voice_text,
            "data": {
                "sample_questions": sample_questions
            }
        }

    def _fallback_greeting(self, lang: str) -> Dict[str, Any]:
        return self._general_agri_response("", lang)

