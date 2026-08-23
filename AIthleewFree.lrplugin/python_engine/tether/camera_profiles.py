"""Profile cấu hình FTP cho từng dòng máy ảnh."""

CAMERA_PROFILES = {
    "sony_a7iii": {
        "name": "Sony A7 III",
        "port": 2121,
        "passive_required": True,
        "directory_hierarchy": "Same",
        "notes": "MENU → Network → FTP Transfer → Host = IP · Port = 2121 · Dir Hierarchy = Same",
    },
    "sony_a7iv": {
        "name": "Sony A7 IV",
        "port": 2121,
        "passive_required": True,
        "directory_hierarchy": "Same",
        "notes": "Firmware 6.01+ (KHÔNG dùng 6.00)",
    },
    "sony_a7rv": {
        "name": "Sony A7R V",
        "port": 2121,
        "passive_required": True,
        "directory_hierarchy": "Same",
    },
    "canon_r5": {
        "name": "Canon EOS R5",
        "port": 2121,  # Camera hiển thị 02121 (5 chữ số)
        "passive_required": True,
        "directory_hierarchy": "Default",
        "notes": "Passive = Enable · Power saving = Disable · Port = 02121",
    },
    "canon_r6mk2": {
        "name": "Canon R6 Mark II",
        "port": 2121,
        "passive_required": True,
        "directory_hierarchy": "Default",
    },
    "nikon_z6ii": {
        "name": "Nikon Z6 II",
        "port": 2121,
        "passive_required": True,
        "directory_hierarchy": "Same",
    },
    "nikon_z8": {
        "name": "Nikon Z8",
        "port": 2121,
        "passive_required": True,
        "directory_hierarchy": "Same",
    },
    "fujifilm_xt5": {
        "name": "Fujifilm X-T5",
        "port": 2121,
        "passive_required": True,
        "directory_hierarchy": "Same",
    },
    "panasonic_s5ii": {
        "name": "Panasonic Lumix S5 II / S5 IIX",
        "port": 2121,
        "passive_required": True,
        "directory_hierarchy": "Same",
        "notes": "MENU → Network → PC Save → Wi-Fi FTP → Host = IP · Port = 2121",
    },
}


def get_profile(camera_id: str) -> dict:
    return CAMERA_PROFILES.get(camera_id, {})


def list_cameras() -> list:
    return [(k, v["name"]) for k, v in CAMERA_PROFILES.items()]

