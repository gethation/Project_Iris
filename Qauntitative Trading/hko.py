import json

data = [{
    "start": "2025-04-18T10:20:00",
    "end":   "2025-04-21T15:20:00",
    "area":[[85673.0, 85441.0], [84442.0, 84319.0]]},
    ]


with open(r"C:\Users\Huang\Work place\Project_Iris\Qauntitative Trading\S&R_Trding\levels.json", 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)
