import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.store.families import FAMILY_CODE_ALPHABET, family_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_store():
    family_store.clear()
    original_ttl = settings.family_ttl_minutes
    yield
    settings.family_ttl_minutes = original_ttl
    family_store.clear()


def test_create_preview_join_and_status_linked_on_both_sides():
    # 1. Create family as student
    create_res = client.post(
        "/families",
        json={"role": "student", "name": "  Aarav Sharma  ", "lang": "en"},
    )
    assert create_res.status_code == 201
    create_data = create_res.json()
    family_code = create_data["family_code"]
    student_token = create_data["member_token"]
    assert create_data["role"] == "student"
    assert "expires_at" in create_data

    # 2. Preview endpoint before partner joins
    preview_res = client.get(f"/families/{family_code}/preview")
    assert preview_res.status_code == 200
    preview_data = preview_res.json()
    assert preview_data["family_code"] == family_code
    assert preview_data["open_role"] == "parent"
    assert preview_data["creator_name"] == "Aarav Sharma"

    # 3. Status before partner joins
    status_res1 = client.get(
        f"/families/{family_code}/status",
        headers={"X-Member-Token": student_token},
    )
    assert status_res1.status_code == 200
    status_data1 = status_res1.json()
    assert status_data1["family_code"] == family_code
    assert status_data1["linked"] is False
    assert status_data1["you"] == {"role": "student", "name": "Aarav Sharma", "done": False}
    assert status_data1["partner"] is None
    assert "member_token" not in status_data1
    assert "member_token" not in status_data1["you"]

    # 4. Join family as parent
    join_res = client.post(
        f"/families/{family_code}/join",
        json={"role": "parent", "name": "Sunita Sharma", "lang": "hi"},
    )
    assert join_res.status_code == 200
    join_data = join_res.json()
    parent_token = join_data["member_token"]
    assert join_data["family_code"] == family_code
    assert join_data["role"] == "parent"
    assert join_data["partner"] == {"role": "student", "name": "Aarav Sharma"}
    assert "expires_at" in join_data

    # 5. Status for student (now linked)
    status_res_student = client.get(
        f"/families/{family_code}/status",
        headers={"X-Member-Token": student_token},
    )
    assert status_res_student.status_code == 200
    student_status = status_res_student.json()
    assert student_status["linked"] is True
    assert student_status["you"] == {"role": "student", "name": "Aarav Sharma", "done": False}
    assert student_status["partner"] == {"role": "parent", "name": "Sunita Sharma", "done": False}

    # 6. Status for parent (now linked)
    status_res_parent = client.get(
        f"/families/{family_code}/status",
        headers={"X-Member-Token": parent_token},
    )
    assert status_res_parent.status_code == 200
    parent_status = status_res_parent.json()
    assert parent_status["linked"] is True
    assert parent_status["you"] == {"role": "parent", "name": "Sunita Sharma", "done": False}
    assert parent_status["partner"] == {"role": "student", "name": "Aarav Sharma", "done": False}

    # 7. Preview after both slots are filled
    preview_res2 = client.get(f"/families/{family_code}/preview")
    assert preview_res2.status_code == 200
    assert preview_res2.json()["open_role"] is None
    assert preview_res2.json()["creator_name"] == "Aarav Sharma"


def test_role_taken():
    create_res = client.post(
        "/families",
        json={"role": "student", "name": "Rohan", "lang": "en"},
    )
    assert create_res.status_code == 201
    code = create_res.json()["family_code"]

    join_res = client.post(
        f"/families/{code}/join",
        json={"role": "student", "name": "Another Student", "lang": "hi"},
    )
    assert join_res.status_code == 409
    err = join_res.json()
    assert "error" in err
    assert err["error"]["code"] == "role_taken"


def test_family_full():
    create_res = client.post(
        "/families",
        json={"role": "student", "name": "Rohan", "lang": "en"},
    )
    code = create_res.json()["family_code"]

    # Join as parent (family now full)
    join_res1 = client.post(
        f"/families/{code}/join",
        json={"role": "parent", "name": "Sunita", "lang": "en"},
    )
    assert join_res1.status_code == 200

    # Try to join 3rd member (with either role)
    join_res2 = client.post(
        f"/families/{code}/join",
        json={"role": "student", "name": "Third Person", "lang": "en"},
    )
    assert join_res2.status_code == 409
    assert join_res2.json()["error"]["code"] == "family_full"


def test_unknown_code_404():
    res1 = client.get("/families/ABC999/preview")
    assert res1.status_code == 404
    assert res1.json()["error"]["code"] == "family_not_found"

    res2 = client.post(
        "/families/ABC999/join",
        json={"role": "parent", "name": "Parent", "lang": "en"},
    )
    assert res2.status_code == 404
    assert res2.json()["error"]["code"] == "family_not_found"

    res3 = client.get(
        "/families/ABC999/status",
        headers={"X-Member-Token": "some-token"},
    )
    assert res3.status_code == 404
    assert res3.json()["error"]["code"] == "family_not_found"


def test_bad_token_401():
    create_res = client.post(
        "/families",
        json={"role": "student", "name": "Rohan", "lang": "en"},
    )
    code = create_res.json()["family_code"]

    # Missing token header
    res_missing = client.get(f"/families/{code}/status")
    assert res_missing.status_code == 401
    assert res_missing.json()["error"]["code"] == "invalid_token"

    # Invalid token header
    res_invalid = client.get(
        f"/families/{code}/status",
        headers={"X-Member-Token": "completely_wrong_token"},
    )
    assert res_invalid.status_code == 401
    assert res_invalid.json()["error"]["code"] == "invalid_token"


def test_expiry():
    # Set TTL to 0
    settings.family_ttl_minutes = 0

    create_res = client.post(
        "/families",
        json={"role": "student", "name": "Rohan", "lang": "en"},
    )
    assert create_res.status_code == 201
    code = create_res.json()["family_code"]
    token = create_res.json()["member_token"]

    # Attempt to preview expired family
    preview_res = client.get(f"/families/{code}/preview")
    assert preview_res.status_code == 404
    assert preview_res.json()["error"]["code"] == "family_not_found"

    # Attempt to join expired family
    join_res = client.post(
        f"/families/{code}/join",
        json={"role": "parent", "name": "Mom", "lang": "en"},
    )
    assert join_res.status_code == 404
    assert join_res.json()["error"]["code"] == "family_not_found"

    # Attempt to get status of expired family
    status_res = client.get(
        f"/families/{code}/status",
        headers={"X-Member-Token": token},
    )
    assert status_res.status_code == 404
    assert status_res.json()["error"]["code"] == "family_not_found"


def test_code_length_and_alphabet():
    codes = set()
    for i in range(10):
        res = client.post(
            "/families",
            json={"role": "student", "name": f"Student {i}", "lang": "en"},
        )
        assert res.status_code == 201
        code = res.json()["family_code"]
        assert len(code) == 6
        assert all(c in FAMILY_CODE_ALPHABET for c in code)
        assert code == code.upper()
        codes.add(code)
    assert len(codes) == 10


def test_lowercase_and_hyphenated_codes_join_fine():
    create_res = client.post(
        "/families",
        json={"role": "student", "name": "Aarav", "lang": "en"},
    )
    code = create_res.json()["family_code"]
    student_token = create_res.json()["member_token"]

    # Manipulate code: lowercase and add hyphen
    manipulated_code = f"{code[:3].lower()}-{code[3:].lower()}"

    # Preview works with lowercase and hyphen
    preview_res = client.get(f"/families/{manipulated_code}/preview")
    assert preview_res.status_code == 200
    assert preview_res.json()["family_code"] == code

    # Join works with spaced and hyphenated code
    spaced_hyphenated_code = f" {code[:3].lower()} - {code[3:].lower()} "
    join_res = client.post(
        f"/families/{spaced_hyphenated_code}/join",
        json={"role": "parent", "name": "Sunita", "lang": "hi"},
    )
    assert join_res.status_code == 200
    parent_token = join_res.json()["member_token"]

    # Status works with manipulated code
    status_res = client.get(
        f"/families/{manipulated_code}/status",
        headers={"X-Member-Token": parent_token},
    )
    assert status_res.status_code == 200
    assert status_res.json()["linked"] is True

    # Status works for student too
    status_res2 = client.get(
        f"/families/{manipulated_code}/status",
        headers={"X-Member-Token": student_token},
    )
    assert status_res2.status_code == 200
    assert status_res2.json()["linked"] is True


def test_validation_errors():
    # Empty name
    res1 = client.post(
        "/families",
        json={"role": "student", "name": "   ", "lang": "en"},
    )
    assert res1.status_code == 422
    assert res1.json()["error"]["code"] == "validation_error"

    # Name too long (> 40 chars)
    res2 = client.post(
        "/families",
        json={"role": "student", "name": "A" * 41, "lang": "en"},
    )
    assert res2.status_code == 422
    assert res2.json()["error"]["code"] == "validation_error"

    # Invalid role
    res3 = client.post(
        "/families",
        json={"role": "teacher", "name": "Aarav", "lang": "en"},
    )
    assert res3.status_code == 422
    assert res3.json()["error"]["code"] == "validation_error"

    # Invalid lang
    res4 = client.post(
        "/families",
        json={"role": "student", "name": "Aarav", "lang": "fr"},
    )
    assert res4.status_code == 422
    assert res4.json()["error"]["code"] == "validation_error"
