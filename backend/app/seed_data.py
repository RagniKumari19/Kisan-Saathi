"""Curated reference data and demo fixtures.

Reference content (crops, diseases, treatments, MSP) carries a source URL and a
verification date. Market prices and weather are demo fixtures in this build and
are labelled as mock everywhere they surface (``provenance.is_mock``).
"""
from __future__ import annotations

DISTRICTS = [
    {"state": "Maharashtra", "name": "Pune", "slug": "maharashtra/pune", "latitude": 18.5204, "longitude": 73.8567, "agro_zone": "WESTERN_PLATEAU"},
    {"state": "Maharashtra", "name": "Nashik", "slug": "maharashtra/nashik", "latitude": 19.9975, "longitude": 73.7898, "agro_zone": "WESTERN_PLATEAU"},
    {"state": "Maharashtra", "name": "Ahmednagar", "slug": "maharashtra/ahmednagar", "latitude": 19.0948, "longitude": 74.7480, "agro_zone": "SCARCE_RAINFALL"},
    {"state": "Maharashtra", "name": "Solapur", "slug": "maharashtra/solapur", "latitude": 17.6599, "longitude": 75.9064, "agro_zone": "SCARCE_RAINFALL"},
    {"state": "Maharashtra", "name": "Kolhapur", "slug": "maharashtra/kolhapur", "latitude": 16.7050, "longitude": 74.2433, "agro_zone": "WESTERN_GHATS"},
    {"state": "Maharashtra", "name": "Satara", "slug": "maharashtra/satara", "latitude": 17.6805, "longitude": 74.0183, "agro_zone": "WESTERN_GHATS"},
    {"state": "Maharashtra", "name": "Nagpur", "slug": "maharashtra/nagpur", "latitude": 21.1458, "longitude": 79.0882, "agro_zone": "CENTRAL_PLATEAU"},
    {"state": "Madhya Pradesh", "name": "Indore", "slug": "madhya-pradesh/indore", "latitude": 22.7196, "longitude": 75.8577, "agro_zone": "CENTRAL_PLATEAU"},
    {"state": "Punjab", "name": "Ludhiana", "slug": "punjab/ludhiana", "latitude": 30.9010, "longitude": 75.8573, "agro_zone": "TRANS_GANGETIC"},
]

_MAH = ["WESTERN_PLATEAU", "SCARCE_RAINFALL", "WESTERN_GHATS", "CENTRAL_PLATEAU"]

CROPS = [
    {"slug": "wheat", "name_en": "Wheat", "name_hi": "गेहूं", "scientific_name": "Triticum aestivum", "category": "cereal", "season": "rabi", "duration_days": 120, "water_need": "medium", "ideal_ph_min": 6.0, "ideal_ph_max": 7.5, "n_target": 120, "p_target": 60, "k_target": 40, "zones": _MAH + ["TRANS_GANGETIC"], "description_en": "Cool-season cereal; sow October–November, harvest March–April.", "description_hi": "ठंडे मौसम की फसल; अक्टूबर–नवंबर में बोएं, मार्च–अप्रैल में कटाई।"},
    {"slug": "chickpea", "name_en": "Chickpea (gram)", "name_hi": "चना", "scientific_name": "Cicer arietinum", "category": "pulse", "season": "rabi", "duration_days": 105, "water_need": "low", "ideal_ph_min": 6.0, "ideal_ph_max": 8.0, "n_target": 25, "p_target": 50, "k_target": 30, "zones": _MAH + ["CENTRAL_PLATEAU"], "description_en": "Low-water rabi pulse; fixes nitrogen and suits black soil.", "description_hi": "कम पानी में होने वाली रबी दलहन; काली मिट्टी के लिए उपयुक्त।"},
    {"slug": "maize", "name_en": "Maize", "name_hi": "मक्का", "scientific_name": "Zea mays", "category": "cereal", "season": "kharif", "duration_days": 100, "water_need": "medium", "ideal_ph_min": 5.8, "ideal_ph_max": 7.5, "n_target": 120, "p_target": 60, "k_target": 50, "zones": _MAH + ["TRANS_GANGETIC", "CENTRAL_PLATEAU"], "description_en": "Fast-growing cereal for kharif and rabi; responsive to nitrogen.", "description_hi": "खरीफ और रबी दोनों में उगने वाला तेज़ बढ़ने वाला अनाज।"},
    {"slug": "rice", "name_en": "Rice (paddy)", "name_hi": "धान", "scientific_name": "Oryza sativa", "category": "cereal", "season": "kharif", "duration_days": 130, "water_need": "high", "ideal_ph_min": 5.5, "ideal_ph_max": 7.0, "n_target": 100, "p_target": 50, "k_target": 50, "zones": ["WESTERN_GHATS", "TRANS_GANGETIC", "CENTRAL_PLATEAU"], "description_en": "Water-intensive kharif cereal; needs assured irrigation or heavy rain.", "description_hi": "अधिक पानी चाहने वाली खरीफ फसल; सिंचाई या भरपूर बारिश ज़रूरी।"},
    {"slug": "jowar", "name_en": "Sorghum (jowar)", "name_hi": "ज्वार", "scientific_name": "Sorghum bicolor", "category": "cereal", "season": "kharif", "duration_days": 110, "water_need": "low", "ideal_ph_min": 6.0, "ideal_ph_max": 8.2, "n_target": 80, "p_target": 40, "k_target": 40, "zones": _MAH, "description_en": "Drought-tolerant cereal for rainfed black-soil districts.", "description_hi": "सूखा सहने वाली फसल, बारानी काली मिट्टी के लिए।"},
    {"slug": "bajra", "name_en": "Pearl millet (bajra)", "name_hi": "बाजरा", "scientific_name": "Pennisetum glaucum", "category": "cereal", "season": "kharif", "duration_days": 85, "water_need": "low", "ideal_ph_min": 6.0, "ideal_ph_max": 8.5, "n_target": 60, "p_target": 30, "k_target": 30, "zones": ["SCARCE_RAINFALL", "CENTRAL_PLATEAU"], "description_en": "Short-duration millet for low-rainfall zones.", "description_hi": "कम बारिश वाले क्षेत्रों के लिए कम अवधि की फसल।"},
    {"slug": "soybean", "name_en": "Soybean", "name_hi": "सोयाबीन", "scientific_name": "Glycine max", "category": "oilseed", "season": "kharif", "duration_days": 100, "water_need": "medium", "ideal_ph_min": 6.0, "ideal_ph_max": 7.5, "n_target": 30, "p_target": 60, "k_target": 40, "zones": _MAH + ["CENTRAL_PLATEAU"], "description_en": "Kharif oilseed; fixes nitrogen, sensitive to waterlogging.", "description_hi": "खरीफ तिलहन; जलभराव से बचाएं।"},
    {"slug": "pigeonpea", "name_en": "Pigeon pea (tur)", "name_hi": "तुअर", "scientific_name": "Cajanus cajan", "category": "pulse", "season": "kharif", "duration_days": 160, "water_need": "low", "ideal_ph_min": 5.8, "ideal_ph_max": 8.0, "n_target": 25, "p_target": 50, "k_target": 30, "zones": _MAH, "description_en": "Long-duration kharif pulse, tolerant of heat and poor soil.", "description_hi": "लंबी अवधि की खरीफ दलहन, गर्मी सहन करती है।"},
    {"slug": "mungbean", "name_en": "Green gram (moong)", "name_hi": "मूंग", "scientific_name": "Vigna radiata", "category": "pulse", "season": "zaid", "duration_days": 70, "water_need": "low", "ideal_ph_min": 6.0, "ideal_ph_max": 7.5, "n_target": 20, "p_target": 40, "k_target": 20, "zones": _MAH, "description_en": "Short summer pulse; good rotation after rabi.", "description_hi": "गर्मी की छोटी दलहन; रबी के बाद अच्छी फसल।"},
    {"slug": "blackgram", "name_en": "Black gram (urad)", "name_hi": "उड़द", "scientific_name": "Vigna mungo", "category": "pulse", "season": "kharif", "duration_days": 75, "water_need": "low", "ideal_ph_min": 6.0, "ideal_ph_max": 7.8, "n_target": 20, "p_target": 40, "k_target": 20, "zones": _MAH, "description_en": "Short kharif pulse; improves soil nitrogen.", "description_hi": "छोटी खरीफ दलहन; मिट्टी में नाइट्रोजन बढ़ाती है।"},
    {"slug": "lentil", "name_en": "Lentil (masoor)", "name_hi": "मसूर", "scientific_name": "Lens culinaris", "category": "pulse", "season": "rabi", "duration_days": 110, "water_need": "low", "ideal_ph_min": 6.0, "ideal_ph_max": 7.8, "n_target": 25, "p_target": 40, "k_target": 25, "zones": _MAH + ["CENTRAL_PLATEAU"], "description_en": "Cool-season pulse; one or two irrigations are usually enough.", "description_hi": "ठंडी रबी दलहन; एक-दो सिंचाई पर्याप्त।"},
    {"slug": "groundnut", "name_en": "Groundnut", "name_hi": "मूंगफली", "scientific_name": "Arachis hypogaea", "category": "oilseed", "season": "kharif", "duration_days": 110, "water_need": "medium", "ideal_ph_min": 6.0, "ideal_ph_max": 7.5, "n_target": 30, "p_target": 50, "k_target": 40, "zones": ["SCARCE_RAINFALL", "WESTERN_PLATEAU", "CENTRAL_PLATEAU"], "description_en": "Kharif oilseed; needs light soil and steady moisture.", "description_hi": "हल्की मिट्टी और नमी वाली खरीफ तिलहन।"},
    {"slug": "mustard", "name_en": "Mustard", "name_hi": "सरसों", "scientific_name": "Brassica juncea", "category": "oilseed", "season": "rabi", "duration_days": 120, "water_need": "low", "ideal_ph_min": 6.0, "ideal_ph_max": 7.8, "n_target": 60, "p_target": 30, "k_target": 30, "zones": ["TRANS_GANGETIC", "CENTRAL_PLATEAU"], "description_en": "Low-water rabi oilseed.", "description_hi": "कम पानी की रबी तिलहन।"},
    {"slug": "cotton", "name_en": "Cotton", "name_hi": "कपास", "scientific_name": "Gossypium hirsutum", "category": "fibre", "season": "kharif", "duration_days": 170, "water_need": "medium", "ideal_ph_min": 6.0, "ideal_ph_max": 8.2, "n_target": 120, "p_target": 60, "k_target": 60, "zones": _MAH, "description_en": "Long-duration cash fibre crop on black soil.", "description_hi": "काली मिट्टी की लंबी अवधि वाली नकदी फसल।"},
    {"slug": "sugarcane", "name_en": "Sugarcane", "name_hi": "गन्ना", "scientific_name": "Saccharum officinarum", "category": "cash", "season": "perennial", "duration_days": 330, "water_need": "high", "ideal_ph_min": 6.0, "ideal_ph_max": 8.0, "n_target": 250, "p_target": 60, "k_target": 60, "zones": ["WESTERN_PLATEAU", "WESTERN_GHATS", "TRANS_GANGETIC"], "description_en": "Year-round crop needing assured irrigation and a sugar mill nearby.", "description_hi": "पूरे साल की फसल; सिंचाई और पास में शुगर मिल ज़रूरी।"},
    {"slug": "onion", "name_en": "Onion", "name_hi": "प्याज", "scientific_name": "Allium cepa", "category": "vegetable", "season": "rabi", "duration_days": 110, "water_need": "medium", "ideal_ph_min": 6.0, "ideal_ph_max": 7.5, "n_target": 100, "p_target": 50, "k_target": 50, "zones": _MAH, "description_en": "Key Nashik cash crop; harvest-and-store economics drive price risk.", "description_hi": "नासिक की प्रमुख नकदी फसल; भंडारण से भाव बदलते हैं।"},
    {"slug": "tomato", "name_en": "Tomato", "name_hi": "टमाटर", "scientific_name": "Solanum lycopersicum", "category": "vegetable", "season": "kharif", "duration_days": 90, "water_need": "medium", "ideal_ph_min": 6.0, "ideal_ph_max": 7.0, "n_target": 120, "p_target": 60, "k_target": 60, "zones": _MAH, "description_en": "Short-cycle vegetable with high market price volatility.", "description_hi": "कम अवधि की सब्ज़ी; बाज़ार भाव में उतार-चढ़ाव।"},
    {"slug": "potato", "name_en": "Potato", "name_hi": "आलू", "scientific_name": "Solanum tuberosum", "category": "vegetable", "season": "rabi", "duration_days": 95, "water_need": "medium", "ideal_ph_min": 5.5, "ideal_ph_max": 6.8, "n_target": 120, "p_target": 60, "k_target": 80, "zones": ["CENTRAL_PLATEAU", "TRANS_GANGETIC", "WESTERN_PLATEAU"], "description_en": "Rabi tuber crop; avoid waterlogging.", "description_hi": "रबी कंद फसल; जलभराव से बचें।"},
    {"slug": "chilli", "name_en": "Chilli", "name_hi": "मिर्च", "scientific_name": "Capsicum annuum", "category": "spice", "season": "kharif", "duration_days": 150, "water_need": "medium", "ideal_ph_min": 6.0, "ideal_ph_max": 7.5, "n_target": 100, "p_target": 50, "k_target": 50, "zones": _MAH, "description_en": "Long-duration spice crop; sensitive to waterlogging and thrips.", "description_hi": "लंबी अवधि की मसाला फसल; जलभराव और थ्रिप्स से बचाएं।"},
    {"slug": "grapes", "name_en": "Grapes", "name_hi": "अंगूर", "scientific_name": "Vitis vinifera", "category": "fruit", "season": "perennial", "duration_days": 180, "water_need": "high", "ideal_ph_min": 6.5, "ideal_ph_max": 7.5, "n_target": 100, "p_target": 50, "k_target": 80, "zones": ["WESTERN_PLATEAU"], "description_en": "Perennial vineyard crop; Nashik and Sangli belts.", "description_hi": "बारहमासी बाग; नासिक और सांगली क्षेत्र।"},
    {"slug": "pomegranate", "name_en": "Pomegranate", "name_hi": "अनार", "scientific_name": "Punica granatum", "category": "fruit", "season": "perennial", "duration_days": 200, "water_need": "low", "ideal_ph_min": 6.5, "ideal_ph_max": 8.0, "n_target": 80, "p_target": 40, "k_target": 60, "zones": ["SCARCE_RAINFALL", "WESTERN_PLATEAU"], "description_en": "Drought-tolerant orchard crop suited to Solapur and Ahmednagar.", "description_hi": "सूखा सहने वाला बाग; सोलापुर और अहमदनगर।"},
    {"slug": "banana", "name_en": "Banana", "name_hi": "केला", "scientific_name": "Musa paradisiaca", "category": "fruit", "season": "perennial", "duration_days": 300, "water_need": "high", "ideal_ph_min": 6.0, "ideal_ph_max": 7.5, "n_target": 200, "p_target": 60, "k_target": 150, "zones": ["WESTERN_GHATS", "WESTERN_PLATEAU"], "description_en": "Irrigated perennial fruit; heavy potassium feeder.", "description_hi": "सिंचाई वाली बारहमासी फसल; पोटाश अधिक चाहिए।"},
    {"slug": "mango", "name_en": "Mango", "name_hi": "आम", "scientific_name": "Mangifera indica", "category": "fruit", "season": "perennial", "duration_days": 300, "water_need": "medium", "ideal_ph_min": 6.0, "ideal_ph_max": 7.5, "n_target": 80, "p_target": 40, "k_target": 60, "zones": ["WESTERN_GHATS", "WESTERN_PLATEAU"], "description_en": "Perennial orchard crop; flowering affected by unseasonal rain.", "description_hi": "बारहमासी बाग; बेमौसम बारिश से फूल प्रभावित।"},
    {"slug": "garlic", "name_en": "Garlic", "name_hi": "लहसुन", "scientific_name": "Allium sativum", "category": "vegetable", "season": "rabi", "duration_days": 130, "water_need": "medium", "ideal_ph_min": 6.0, "ideal_ph_max": 7.5, "n_target": 90, "p_target": 50, "k_target": 50, "zones": _MAH, "description_en": "Rabi bulb crop; curing and storage affect sale price.", "description_hi": "रबी कंद फसल; सुखाने और भंडारण से भाव तय होता है।"},
]

# slug, crop, names, pathogen, symptoms, spread, severity, risk band
DISEASES = [
    {
        "slug": "tomato__early_blight", "crop_slug": "tomato", "name_en": "Early blight", "name_hi": "टमाटर अगेती झुलसा",
        "pathogen_type": "fungal", "severity_default": 3, "risk_humidity_min": 80, "risk_temp_min": 24, "risk_temp_max": 32,
        "symptoms_en": "Brown spots with concentric rings on lower leaves first; leaves yellow and drop. Fruit may show dark sunken spots near the stem.",
        "symptoms_hi": "नीचे की पत्तियों पर गोल छल्लेदार भूरे धब्बे; पत्तियां पीली होकर गिरती हैं। फल पर तने के पास गहरे धब्बे।",
        "spread_en": "Soil splash, infected seed and crop debris. Warm, humid weather favours it.",
        "treatments": [
            {"kind": "cultural", "title": "Remove and destroy infected lower leaves", "detail": "Pick affected leaves early in the day and remove them from the field. Stake plants so leaves do not touch the soil.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases_veg.html", "order": 1},
            {"kind": "organic", "title": "Neem-based spray for early stages", "detail": "Spray azadirachtin 1500 ppm at 5 ml/L at first sign, repeat after 7 days if needed. Not a cure; slows spread.", "dosage": "5 ml/L water", "safety_notes": "Spray in the evening; keep away from water sources.", "source_url": "https://agritech.tnau.ac.in/organic_farming/organic_pest.html", "order": 2},
            {"kind": "chemical", "title": "Mancozeb 75% WP", "detail": "Preventive spray when prolonged humid weather is forecast; cover both leaf surfaces.", "dosage": "2 g/L water, about 200 L/acre", "safety_notes": "Wear gloves and a mask. Do not spray within 7 days of harvest. Rotate with a different group to avoid resistance.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases_veg.html", "order": 3},
        ],
    },
    {
        "slug": "tomato__late_blight", "crop_slug": "tomato", "name_en": "Late blight", "name_hi": "टमाटर पछेती झुलसा",
        "pathogen_type": "fungal", "severity_default": 5, "risk_humidity_min": 85, "risk_temp_min": 15, "risk_temp_max": 24,
        "symptoms_en": "Large water-soaked grey-green patches on leaves; white fuzzy growth underneath in wet weather. Whole plant can collapse within days.",
        "symptoms_hi": "पत्तियों पर बड़े पानी जैसे धब्बे; नमी में नीचे सफेद फंगस। कुछ दिनों में पूरा पौधा गिर सकता है।",
        "spread_en": "Wind-borne spores and infected seedlings. Cool, wet weather drives outbreaks.",
        "treatments": [
            {"kind": "cultural", "title": "Remove infected plants and avoid overhead irrigation", "detail": "Uproot heavily infected plants, bag them and destroy away from the field. Water at the base, not the canopy.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases_veg.html", "order": 1},
            {"kind": "chemical", "title": "Cymoxanil + Mancozeb", "detail": "Use at first sign in cool, wet weather; alternate with a protectant to manage resistance.", "dosage": "2 g/L water", "safety_notes": "Pre-harvest interval 7 days. Wear PPE. Follow the label and local extension advice.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases_veg.html", "order": 2},
        ],
    },
    {
        "slug": "tomato__leaf_mold", "crop_slug": "tomato", "name_en": "Leaf mold", "name_hi": "टमाटर पत्ती फफूंद",
        "pathogen_type": "fungal", "severity_default": 2, "risk_humidity_min": 85, "risk_temp_min": 20, "risk_temp_max": 28,
        "symptoms_en": "Pale yellow patches on upper leaves with olive-green to brown velvet-like growth underneath.",
        "symptoms_hi": "ऊपर की पत्तियों पर हल्के पीले धब्बे; नीचे जैतूनी रंग का मखमली फंगस।",
        "spread_en": "High humidity in dense canopies; spores spread on hands, tools and air.",
        "treatments": [
            {"kind": "cultural", "title": "Increase airflow and reduce canopy humidity", "detail": "Prune lower leaves, widen spacing and ventilate polyhouses. Drip irrigation instead of overhead.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases_veg.html", "order": 1},
        ],
    },
    {
        "slug": "tomato__bacterial_spot", "crop_slug": "tomato", "name_en": "Bacterial spot", "name_hi": "टमाटर जीवाणु धब्बा",
        "pathogen_type": "bacterial", "severity_default": 3, "risk_humidity_min": 80, "risk_temp_min": 24, "risk_temp_max": 30,
        "symptoms_en": "Small dark water-soaked spots on leaves and fruit; spots scab over and leaves yellow.",
        "symptoms_hi": "पत्तियों और फल पर छोटे गहरे पानी जैसे धब्बे; बाद में पपड़ी बनती है।",
        "spread_en": "Contaminated seed, rain splash and handling wet plants.",
        "treatments": [
            {"kind": "cultural", "title": "Use clean seed and do not handle wet plants", "detail": "Buy certified seed, rotate away from tomato/potato for two seasons, and remove crop residue after harvest.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases_veg.html", "order": 1},
            {"kind": "chemical", "title": "Copper oxychloride", "detail": "Copper-based protectant reduces spread; it does not cure existing spots.", "dosage": "3 g/L water", "safety_notes": "Do not mix with strongly acidic products. Follow label interval.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases_veg.html", "order": 2},
        ],
    },
    {
        "slug": "cotton__leaf_curl", "crop_slug": "cotton", "name_en": "Cotton leaf curl", "name_hi": "कपास पत्ती मरोड़",
        "pathogen_type": "viral", "severity_default": 4, "risk_humidity_min": 60, "risk_temp_min": 25, "risk_temp_max": 35,
        "symptoms_en": "Upward curling and cupping of leaves, thickened veins, small leaf-like growths under leaves. Plants stunted.",
        "symptoms_hi": "पत्तियां ऊपर मुड़ना, नसें मोटी, नीचे छोटी पत्ती जैसी वृद्धि। पौधा छोटा रह जाता है।",
        "spread_en": "Spread by whitefly; not by seed or tools.",
        "treatments": [
            {"kind": "cultural", "title": "Manage whitefly and remove infected plants", "detail": "Use yellow sticky traps, avoid excess nitrogen, and rogue out severely affected plants early. Grow a whitefly-tolerant variety next season.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases.html", "order": 1},
            {"kind": "chemical", "title": "Whitefly control — follow local recommendation", "detail": "Because resistance develops quickly, use only a product recommended by your local KVK and rotate modes of action.", "safety_notes": "Never mix multiple insecticides. Observe the pre-harvest interval strictly.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases.html", "order": 2},
        ],
    },
    {
        "slug": "cotton__bollworm", "crop_slug": "cotton", "name_en": "Pink bollworm", "name_hi": "कपास गुलाबी सुंडी",
        "pathogen_type": "pest", "severity_default": 4, "risk_humidity_min": 50, "risk_temp_min": 25, "risk_temp_max": 35,
        "symptoms_en": "Rosetted flowers, bored bolls with exit holes, pink caterpillars inside bolls. Shedding of squares and bolls.",
        "symptoms_hi": "फूल गुच्छे में बंद, टिंडों में छेद, अंदर गुलाबी सुंडी। कलियां और टिंडे गिरना।",
        "spread_en": "Moths lay eggs on buds and bolls; populations build through the season.",
        "treatments": [
            {"kind": "cultural", "title": "Pheromone traps and timely termination", "detail": "Install 4–5 pheromone traps per acre to monitor moth flight. Destroy crop residue after harvest; do not leave bolls in the field.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20pests.html", "order": 1},
            {"kind": "organic", "title": "Bacillus thuringiensis spray", "detail": "Use Bt formulation in the evening when larvae are young.", "dosage": "1–2 g/L water", "safety_notes": "Not effective on larvae already inside bolls.", "source_url": "https://agritech.tnau.ac.in/organic_farming/organic_pest.html", "order": 2},
        ],
    },
    {
        "slug": "wheat__yellow_rust", "crop_slug": "wheat", "name_en": "Yellow rust", "name_hi": "गेहूं पीला रतुआ",
        "pathogen_type": "fungal", "severity_default": 4, "risk_humidity_min": 80, "risk_temp_min": 8, "risk_temp_max": 20,
        "symptoms_en": "Bright yellow powdery stripes on leaves in rows; dust rubs off on fingers. Spreads fast in cool, humid weather.",
        "symptoms_hi": "पत्तियों पर चमकीली पीली धारियां; उंगली पर पाउडर लगता है। ठंडे-नम मौसम में तेज़ी से फैलता है।",
        "spread_en": "Wind-borne spores from infected fields and volunteer wheat.",
        "treatments": [
            {"kind": "cultural", "title": "Sow rust-resistant varieties and avoid late sowing", "detail": "Use a variety recommended for your district and remove volunteer wheat that carries the fungus between seasons.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases.html", "order": 1},
            {"kind": "chemical", "title": "Propiconazole 25% EC", "detail": "Spray at first sign and repeat after 15 days if the weather stays favourable to rust.", "dosage": "1 ml/L water, about 200 L/acre", "safety_notes": "Do not exceed two sprays per season. Observe the label pre-harvest interval.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases.html", "order": 2},
        ],
    },
    {
        "slug": "onion__purple_blotch", "crop_slug": "onion", "name_en": "Purple blotch", "name_hi": "प्याज बैंगनी धब्बा",
        "pathogen_type": "fungal", "severity_default": 3, "risk_humidity_min": 80, "risk_temp_min": 20, "risk_temp_max": 30,
        "symptoms_en": "Small white lesions that enlarge into purple-centred spots with yellow halos on leaves.",
        "symptoms_hi": "पत्तियों पर सफेद धब्बे जो बैंगनी केंद्र और पीले घेरे वाले हो जाते हैं।",
        "spread_en": "Seed and crop debris; splash dispersal during rain or overhead irrigation.",
        "treatments": [
            {"kind": "cultural", "title": "Rotate crops and avoid overhead irrigation", "detail": "Rotate with a non-allium crop for two seasons; remove infected leaf tips and debris.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases_veg.html", "order": 1},
            {"kind": "chemical", "title": "Mancozeb 75% WP", "detail": "Preventive spray at 10–12 day intervals in humid weather.", "dosage": "2 g/L water", "safety_notes": "Follow the label; wear PPE and observe the pre-harvest interval.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases_veg.html", "order": 2},
        ],
    },
    {
        "slug": "grapes__downy_mildew", "crop_slug": "grapes", "name_en": "Downy mildew", "name_hi": "अंगूर डाउनी फफूंद",
        "pathogen_type": "fungal", "severity_default": 5, "risk_humidity_min": 85, "risk_temp_min": 20, "risk_temp_max": 28,
        "symptoms_en": "Yellow oil-spot patches on upper leaf surface with dense white growth underneath; shoots and berries can be affected.",
        "symptoms_hi": "पत्ती के ऊपर पीले तेल जैसे धब्बे, नीचे सफेद घना फंगस; टहनियां और दाने भी प्रभावित।",
        "spread_en": "Rain splash and high humidity; epidemic risk during cloudy wet spells.",
        "treatments": [
            {"kind": "cultural", "title": "Open the canopy and remove infected leaves", "detail": "Improve air movement, avoid evening irrigation, and remove infected leaves from the vineyard.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases.html", "order": 1},
            {"kind": "chemical", "title": "Metalaxyl + Mancozeb", "detail": "Use as a protectant before a wet spell; rotate with another mode of action after two sprays.", "dosage": "2 g/L water", "safety_notes": "Grape pre-harvest intervals are strict; check the label and export residue limits.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases.html", "order": 2},
        ],
    },
    {
        "slug": "pomegranate__bacterial_blight", "crop_slug": "pomegranate", "name_en": "Bacterial blight (oily spot)", "name_hi": "अनार जीवाणु झुलसा",
        "pathogen_type": "bacterial", "severity_default": 4, "risk_humidity_min": 70, "risk_temp_min": 25, "risk_temp_max": 35,
        "symptoms_en": "Small water-soaked oily spots on leaves, stems and fruit; fruit cracks and blackens.",
        "symptoms_hi": "पत्ती, तना और फल पर छोटे तेल जैसे धब्बे; फल फटकर काला होता है।",
        "spread_en": "Rain splash, pruning tools and infected planting material.",
        "treatments": [
            {"kind": "cultural", "title": "Sterilise pruning tools and remove infected branches", "detail": "Disinfect secateurs between trees, prune during dry weather, and destroy infected material away from the orchard.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases.html", "order": 1},
            {"kind": "chemical", "title": "Copper-based bactericide", "detail": "Apply according to local extension advice around pruning and fruit-set.", "dosage": "As per label", "safety_notes": "Copper accumulates in soil; do not exceed the recommended number of sprays.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases.html", "order": 2},
        ],
    },
    {
        "slug": "maize__fall_armyworm", "crop_slug": "maize", "name_en": "Fall armyworm", "name_hi": "मक्का फॉल आर्मीवर्म",
        "pathogen_type": "pest", "severity_default": 4, "risk_humidity_min": 55, "risk_temp_min": 22, "risk_temp_max": 35,
        "symptoms_en": "Ragged whorl leaves with wet sawdust-like frass; caterpillars with an inverted Y on the head.",
        "symptoms_hi": "पत्तियों में फटे किनारे और गोभी जैसा मल; सुंडी के सिर पर उल्टा Y निशान।",
        "spread_en": "Moths fly long distances; larvae feed inside the whorl.",
        "treatments": [
            {"kind": "cultural", "title": "Scout whorls twice a week and hand-pick larvae", "detail": "Check 20 plants in five spots. Small plots can be managed by hand-picking and destroying larvae.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20pests.html", "order": 1},
            {"kind": "organic", "title": "Neem seed kernel extract", "detail": "Spray into the whorl for young larvae; repeat after 5–7 days.", "dosage": "5% NSKE", "safety_notes": "Spray in the evening.", "source_url": "https://agritech.tnau.ac.in/organic_farming/organic_pest.html", "order": 2},
        ],
    },
    {
        "slug": "rice__blast", "crop_slug": "rice", "name_en": "Rice blast", "name_hi": "धान झुलसा",
        "pathogen_type": "fungal", "severity_default": 4, "risk_humidity_min": 85, "risk_temp_min": 20, "risk_temp_max": 30,
        "symptoms_en": "Spindle-shaped spots with grey centres and brown margins on leaves; neck can rot and panicles fall.",
        "symptoms_hi": "पत्तियों पर तकली के आकार के धब्बे, बीच में धूसर; गर्दन सड़कर बालियां गिरती हैं।",
        "spread_en": "Wind and seed-borne; excess nitrogen increases severity.",
        "treatments": [
            {"kind": "cultural", "title": "Avoid excess nitrogen and use clean seed", "detail": "Split nitrogen doses, keep standing water shallow, and burn or plough in infected stubble.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases.html", "order": 1},
            {"kind": "chemical", "title": "Tricyclazole 75% WP", "detail": "Spray at the boot-leaf stage and again at 50% flowering if blast is present.", "dosage": "0.6 g/L water", "safety_notes": "Follow the label; observe the pre-harvest interval.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases.html", "order": 2},
        ],
    },
    {
        "slug": "potato__late_blight", "crop_slug": "potato", "name_en": "Potato late blight", "name_hi": "आलू पछेती झुलसा",
        "pathogen_type": "fungal", "severity_default": 5, "risk_humidity_min": 85, "risk_temp_min": 15, "risk_temp_max": 24,
        "symptoms_en": "Water-soaked dark patches on leaves and stems; white mould on leaf undersides in wet weather. Tubers rot.",
        "symptoms_hi": "पत्तियों और तनों पर पानी जैसे गहरे धब्बे; नमी में नीचे सफेद फंगस। कंद सड़ते हैं।",
        "spread_en": "Wind-borne spores, infected seed tubers and rain splash.",
        "treatments": [
            {"kind": "cultural", "title": "Use healthy seed tubers and earth up ridges", "detail": "Discard rotting tubers, maintain ridges to protect tubers, and remove infected haulm before harvest.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases_veg.html", "order": 1},
            {"kind": "chemical", "title": "Mancozeb 75% WP", "detail": "Protectant spray when cool, humid weather is forecast; repeat as per label.", "dosage": "2 g/L water", "safety_notes": "Wear PPE; observe the pre-harvest interval.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases_veg.html", "order": 2},
        ],
    },
    {
        "slug": "chilli__anthracnose", "crop_slug": "chilli", "name_en": "Anthracnose (fruit rot)", "name_hi": "मिर्च एंथ्रेक्नोज",
        "pathogen_type": "fungal", "severity_default": 3, "risk_humidity_min": 85, "risk_temp_min": 25, "risk_temp_max": 32,
        "symptoms_en": "Sunken circular spots on ripe fruit with pinkish spore masses in wet weather.",
        "symptoms_hi": "पके फल पर गोल धंसे धब्बे; नमी में गुलाबी बीजाणु दिखते हैं।",
        "spread_en": "Seed-borne and rain splash; overlapping harvests keep inoculum alive.",
        "treatments": [
            {"kind": "cultural", "title": "Remove infected fruit and rotate crops", "detail": "Collect infected fruit in a bag and destroy it. Rotate with a non-solanaceous crop.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases_veg.html", "order": 1},
            {"kind": "chemical", "title": "Carbendazim 50% WP", "detail": "Spray at fruit-set and repeat per label in humid weather.", "dosage": "1 g/L water", "safety_notes": "Observe the pre-harvest interval strictly; do not spray on harvested fruit.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases_veg.html", "order": 2},
        ],
    },
    {
        "slug": "banana__panama_wilt", "crop_slug": "banana", "name_en": "Panama wilt", "name_hi": "केला पनामा विल्ट",
        "pathogen_type": "fungal", "severity_default": 5, "risk_humidity_min": 60, "risk_temp_min": 24, "risk_temp_max": 32,
        "symptoms_en": "Yellowing of lower leaves that splits at the base; a clean cut shows dark streaks in the stem.",
        "symptoms_hi": "नीचे की पत्तियां पीली और आधार पर फटना; तना काटने पर गहरी धारियां।",
        "spread_en": "Infected suckers, soil and farm tools; the fungus survives in soil for years.",
        "treatments": [
            {"kind": "cultural", "title": "Use tissue-culture planting material and quarantine tools", "detail": "Never plant suckers from an affected plot. Clean tools with disinfectant between blocks. There is no field cure once a plant wilts.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases.html", "order": 1},
        ],
    },
    {
        "slug": "wheat__powdery_mildew", "crop_slug": "wheat", "name_en": "Powdery mildew", "name_hi": "गेहूं चूर्णिल आसिता",
        "pathogen_type": "fungal", "severity_default": 2, "risk_humidity_min": 75, "risk_temp_min": 15, "risk_temp_max": 25,
        "symptoms_en": "White powdery patches on leaves and stems; leaves yellow and dry prematurely.",
        "symptoms_hi": "पत्तियों और तनों पर सफेद पाउडर जैसे धब्बे; पत्तियां समय से पहले पीली।",
        "spread_en": "Wind-borne spores; dense crop and high nitrogen favour it.",
        "treatments": [
            {"kind": "cultural", "title": "Avoid dense sowing and excess nitrogen", "detail": "Keep the recommended seed rate and split nitrogen applications.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases.html", "order": 1},
            {"kind": "chemical", "title": "Sulphur 80% WP", "detail": "Spray at first sign; do not apply in hot midday sun.", "dosage": "2 g/L water", "safety_notes": "Avoid spraying above 32 °C; observe the label.", "source_url": "https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases.html", "order": 2},
        ],
    },
]

COMMODITIES = [
    {"slug": "onion", "name_en": "Onion", "name_hi": "प्याज", "category": "vegetable", "aliases": ["Onion", "Pyaz"]},
    {"slug": "tomato", "name_en": "Tomato", "name_hi": "टमाटर", "category": "vegetable", "aliases": ["Tomato"]},
    {"slug": "potato", "name_en": "Potato", "name_hi": "आलू", "category": "vegetable", "aliases": ["Potato"]},
    {"slug": "wheat", "name_en": "Wheat", "name_hi": "गेहूं", "category": "cereal", "aliases": ["Wheat", "Gehun"]},
    {"slug": "rice", "name_en": "Rice", "name_hi": "धान", "category": "cereal", "aliases": ["Rice", "Paddy"]},
    {"slug": "maize", "name_en": "Maize", "name_hi": "मक्का", "category": "cereal", "aliases": ["Maize", "Makka"]},
    {"slug": "jowar", "name_en": "Sorghum", "name_hi": "ज्वार", "category": "cereal", "aliases": ["Jowar", "Sorghum"]},
    {"slug": "bajra", "name_en": "Pearl millet", "name_hi": "बाजरा", "category": "cereal", "aliases": ["Bajra", "Pearl Millet"]},
    {"slug": "cotton", "name_en": "Cotton", "name_hi": "कपास", "category": "fibre", "aliases": ["Cotton", "Kapas"]},
    {"slug": "soybean", "name_en": "Soybean", "name_hi": "सोयाबीन", "category": "oilseed", "aliases": ["Soyabean", "Soybean"]},
    {"slug": "chickpea", "name_en": "Chickpea", "name_hi": "चना", "category": "pulse", "aliases": ["Bengal Gram", "Chana", "Gram"]},
    {"slug": "pigeonpea", "name_en": "Pigeon pea", "name_hi": "तुअर", "category": "pulse", "aliases": ["Tur", "Arhar", "Pigeon Pea"]},
    {"slug": "groundnut", "name_en": "Groundnut", "name_hi": "मूंगफली", "category": "oilseed", "aliases": ["Groundnut", "Moongphali"]},
    {"slug": "mustard", "name_en": "Mustard", "name_hi": "सरसों", "category": "oilseed", "aliases": ["Mustard", "Sarson"]},
    {"slug": "grapes", "name_en": "Grapes", "name_hi": "अंगूर", "category": "fruit", "aliases": ["Grapes", "Angoor"]},
    {"slug": "pomegranate", "name_en": "Pomegranate", "name_hi": "अनार", "category": "fruit", "aliases": ["Pomegranate", "Anar"]},
    {"slug": "banana", "name_en": "Banana", "name_hi": "केला", "category": "fruit", "aliases": ["Banana", "Kela"]},
    {"slug": "mango", "name_en": "Mango", "name_hi": "आम", "category": "fruit", "aliases": ["Mango", "Aam"]},
    {"slug": "garlic", "name_en": "Garlic", "name_hi": "लहसुन", "category": "vegetable", "aliases": ["Garlic", "Lahsun"]},
    {"slug": "chilli", "name_en": "Chilli", "name_hi": "मिर्च", "category": "spice", "aliases": ["Chilli", "Mirchi"]},
    {"slug": "mungbean", "name_en": "Green gram", "name_hi": "मूंग", "category": "pulse", "aliases": ["Moong", "Green Gram"]},
    {"slug": "blackgram", "name_en": "Black gram", "name_hi": "उड़द", "category": "pulse", "aliases": ["Urad", "Black Gram"]},
    {"slug": "lentil", "name_en": "Lentil", "name_hi": "मसूर", "category": "pulse", "aliases": ["Masoor", "Lentil"]},
]

MARKETS = [
    {"district": "maharashtra/pune", "name": "Pune (Gultekdi)", "lat": 18.5018, "lon": 73.8636},
    {"district": "maharashtra/pune", "name": "Shirur", "lat": 18.5223, "lon": 74.1187},
    {"district": "maharashtra/pune", "name": "Baramati", "lat": 18.1514, "lon": 74.5815},
    {"district": "maharashtra/nashik", "name": "Nashik", "lat": 19.9975, "lon": 73.7898},
    {"district": "maharashtra/nashik", "name": "Pimpalgaon", "lat": 20.1667, "lon": 73.9833},
    {"district": "maharashtra/nashik", "name": "Lasalgaon", "lat": 20.1500, "lon": 74.2333},
    {"district": "maharashtra/ahmednagar", "name": "Ahmednagar", "lat": 19.0948, "lon": 74.7480},
    {"district": "maharashtra/ahmednagar", "name": "Rahuri", "lat": 19.3833, "lon": 74.6500},
    {"district": "maharashtra/solapur", "name": "Solapur", "lat": 17.6599, "lon": 75.9064},
    {"district": "maharashtra/solapur", "name": "Barshi", "lat": 18.2333, "lon": 75.6833},
    {"district": "maharashtra/kolhapur", "name": "Kolhapur", "lat": 16.7050, "lon": 74.2433},
    {"district": "maharashtra/satara", "name": "Satara", "lat": 17.6805, "lon": 74.0183},
    {"district": "maharashtra/satara", "name": "Karad", "lat": 17.2896, "lon": 74.1808},
    {"district": "maharashtra/nagpur", "name": "Nagpur (Kalamna)", "lat": 21.1458, "lon": 79.0882},
    {"district": "madhya-pradesh/indore", "name": "Indore (Choithram)", "lat": 22.7196, "lon": 75.8577},
    {"district": "punjab/ludhiana", "name": "Ludhiana", "lat": 30.9010, "lon": 75.8573},
]

# Price generation looks these up; missing commodities simply have no demo rows.
BASE_PRICES = {
    "onion": 1750, "tomato": 1400, "potato": 1300, "wheat": 2450, "rice": 2900,
    "maize": 2200, "jowar": 2900, "bajra": 2400, "cotton": 7100, "soybean": 4900,
    "chickpea": 5600, "pigeonpea": 7800, "groundnut": 6900, "mustard": 5800,
    "grapes": 5200, "pomegranate": 8500, "banana": 1600, "mango": 6500,
    "garlic": 4200, "chilli": 6800, "mungbean": 8600, "blackgram": 9000, "lentil": 6600,
}

MSP_RATES = [
    {"commodity": "wheat", "season": "rabi", "marketing_year": "2025-26", "price": 2425},
    {"commodity": "chickpea", "season": "rabi", "marketing_year": "2025-26", "price": 5650},
    {"commodity": "lentil", "season": "rabi", "marketing_year": "2025-26", "price": 6700},
    {"commodity": "mustard", "season": "rabi", "marketing_year": "2025-26", "price": 5950},
    {"commodity": "rice", "season": "kharif", "marketing_year": "2025-26", "price": 2369},
    {"commodity": "maize", "season": "kharif", "marketing_year": "2025-26", "price": 2400},
    {"commodity": "jowar", "season": "kharif", "marketing_year": "2025-26", "price": 3371},
    {"commodity": "bajra", "season": "kharif", "marketing_year": "2025-26", "price": 2775},
    {"commodity": "pigeonpea", "season": "kharif", "marketing_year": "2025-26", "price": 8000},
    {"commodity": "mungbean", "season": "kharif", "marketing_year": "2025-26", "price": 8768},
    {"commodity": "blackgram", "season": "kharif", "marketing_year": "2025-26", "price": 9125},
    {"commodity": "groundnut", "season": "kharif", "marketing_year": "2025-26", "price": 7263},
    {"commodity": "soybean", "season": "kharif", "marketing_year": "2025-26", "price": 5328},
    {"commodity": "cotton", "season": "kharif", "marketing_year": "2025-26", "price": 7710},
]

MSP_SOURCE = (
    "https://agricoop.nic.in/en/MSP-2025-26"
)
