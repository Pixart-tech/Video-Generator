import json
import os
import sys

try:
    import requests
except ModuleNotFoundError as exc:
    print("Missing dependency 'requests'. Please install it via 'pip install requests'.", file=sys.stderr)
    sys.exit(1)

URL = "https://gate.whapi.cloud/groups?count=500"

HEADERS = {
    "accept": "application/json",
    "authorization": "Bearer GdSRYwWWpJwvjhavIJrRjDSMcRbtTMQb",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "groups.json")
SCHOOLS_FILE = os.path.join(BASE_DIR, "schools.json")
IMAGES_DIR = os.path.join(BASE_DIR, "IMAGES")


def _collect_image_names():
    if not os.path.isdir(IMAGES_DIR):
        return set()
    names = set()
    for entry in os.listdir(IMAGES_DIR):
        base_name, _ = os.path.splitext(entry)
        names.add(base_name)
    return names


def _load_existing_schools():
    if not os.path.exists(SCHOOLS_FILE):
        return {"schools": []}
    try:
        with open(SCHOOLS_FILE, "r", encoding="utf-8") as fp:
            payload = json.load(fp)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Unable to read existing schools.json: {exc}", file=sys.stderr)
        return {"schools": []}

    if not isinstance(payload, dict):
        print("schools.json has unexpected contents; resetting.", file=sys.stderr)
        return {"schools": []}

    schools = payload.get("schools")
    if not isinstance(schools, list):
        print("schools.json missing 'schools' list; resetting.", file=sys.stderr)
        return {"schools": []}

    return {"schools": schools}


def main():
    try:
        response = requests.get(URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        print(f"Error fetching groups: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"Failed to write groups.json: {exc}", file=sys.stderr)
        sys.exit(1)

    image_names = _collect_image_names()
    schools_payload = _load_existing_schools()
    existing_ids = {
        school.get("id") for school in schools_payload.get("schools", [])
        if isinstance(school, dict)
    }
    new_entries = 0
    for group in data.get("groups", []):
        group_id = group.get("id", "")
        if not group_id or group_id in existing_ids:
            continue
        normalized_id = group_id.replace("@g.us", "")
        schools_payload.setdefault("schools", []).append({
            "id": group_id,
            "name": group.get("name", ""),
            "image_status": "yes" if normalized_id in image_names else "no",
            "drive_link": "",
        })
        existing_ids.add(group_id)
        new_entries += 1

    should_write_schools = new_entries > 0 or not os.path.exists(SCHOOLS_FILE)
    if should_write_schools:
        try:
            with open(SCHOOLS_FILE, "w", encoding="utf-8") as fp:
                json.dump(schools_payload, fp, ensure_ascii=False, indent=2)
        except OSError as exc:
            print(f"Failed to write schools.json: {exc}", file=sys.stderr)
            sys.exit(1)
        if new_entries:
            print(f"Added {new_entries} new schools.")
        elif not schools_file_existed:
            print("Created schools.json with existing entries.")
        if drive_updates:
            print(f"Updated {drive_updates} drive links.")
    else:
        print("No new schools to add.")


if __name__ == "__main__":
    main()
