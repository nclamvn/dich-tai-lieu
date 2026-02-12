"""
Prompts for Vietnamese Adapter Agent

Adapts screenplay content for Vietnamese cultural context:
- Honorifics and pronouns
- Cultural references
- Location names
- Dialogue nuances
"""

SYSTEM_PROMPT = """Ban la chuyen gia chuyen the van hoa Viet Nam cho dien anh voi kinh nghiem sau rong ve:

- Van hoa va phong tuc Viet Nam qua cac thoi ky
- Ngon ngu va cach xung ho trong gia dinh, xa hoi
- Su khac biet vung mien (Bac, Trung, Nam)
- Dien anh Viet Nam duong dai va truyen thong
- Chuyen the tac pham van hoc Viet

Nhiem vu cua ban la dam bao kich ban phan anh dung van hoa Viet Nam, tu nhien va chan thuc."""

ADAPTATION_PROMPT = """Chinh sua van hoa cho canh kich ban sau de phu hop voi boi canh Viet Nam.

THONG TIN CANH:
- So canh: {scene_number}
- Boi canh: {setting}
- Thoi ky: {time_period}
- Vung mien: {region}

NHAN VAT:
{character_info}

NOI DUNG CANH HIEN TAI:
{current_scene_content}

Thuc hien chinh sua va tra ve JSON:

```json
{{
    "scene_number": {scene_number},

    "location_adaptation": {{
        "original": "Ten dia diem goc",
        "adapted": "Ten dia diem phu hop van hoa Viet",
        "notes": "Ly do chinh sua"
    }},

    "dialogue_adaptations": [
        {{
            "original_character": "Ten nhan vat",
            "original_dialogue": "Cau thoai goc",
            "adapted_dialogue": "Cau thoai da chinh sua",
            "honorific_used": "Dai tu xung ho su dung",
            "cultural_notes": "Ghi chu van hoa"
        }}
    ],

    "action_adaptations": [
        {{
            "original": "Mo ta hanh dong goc",
            "adapted": "Mo ta da chinh sua cho phu hop van hoa",
            "cultural_element": "Yeu to van hoa duoc them/chinh"
        }}
    ],

    "cultural_additions": [
        {{
            "type": "prop|custom|setting|dialogue",
            "description": "Mo ta yeu to van hoa duoc them",
            "reason": "Ly do them"
        }}
    ],

    "regional_notes": "Ghi chu ve dac diem vung mien",

    "historical_accuracy": "Ghi chu ve do chinh xac lich su (neu ap dung)"
}}
```

HUONG DAN CHINH SUA:

1. DAI TU XUNG HO:
   - Trong gia dinh: con-bo/me, chau-ong/ba, em-anh/chi
   - Ngoai xa hoi: toi-anh/chi, chau-bac/co/chu
   - The hien kinh trong qua cach xung ho
   - Chu y su thay doi xung ho theo cam xuc

2. BOI CANH:
   - Kien truc: nha ong, nha co, chung cu, biet thu
   - Khong gian: san vuon, ban tho, phong khach
   - Thoi tiet: mua phun, nang gat, gio mua

3. PHONG TUC:
   - An uong: bua com gia dinh, tra nuoc
   - Le nghi: cung gio, dam cuoi, dam tang
   - Giao tiep: cach chao hoi, tang qua

4. VUNG MIEN:
   - Bac: kin dao, le nghi, giong Ha Noi
   - Trung: thang than, giong Hue/Da Nang
   - Nam: coi mo, than thien, giong Sai Gon

5. THOI KY LICH SU:
   - Phong kien: quan lai, lang xa
   - Thuoc Phap: pha tron Dong-Tay
   - Hien dai: do thi hoa, cong nghe

Chi tra loi bang JSON object."""
