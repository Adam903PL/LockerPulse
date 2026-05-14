from locker_pulse_api.services.scoring import NO_DATA_WARNING, score_point


def base_point(**overrides):
    point = {
        "status": "Operating",
        "distance": 120,
        "location_247": True,
        "easy_access_zone": True,
        "functions": ["parcel_collect", "parcel_send", "parcel_reverse_return_send"],
        "physical_type": "newfm",
        "image_url": "https://static.easypack24.net/points/pl/images/WAW198M.jpg",
        "address": {"line1": "Marszalkowska 1", "line2": "00-001 Warszawa"},
        "locker_availability": {"status": "NO_DATA"},
    }
    point.update(overrides)
    return point


def test_operating_modern_locker_scores_high():
    result = score_point(base_point(), requested_functions=[], radius_m=3000)

    assert result.score >= 90
    assert result.grade == "excellent"
    assert "Punkt działa poprawnie" in result.reasons


def test_non_operating_point_loses_status_points():
    result = score_point(base_point(status="Disabled"), requested_functions=[], radius_m=3000)

    assert result.score <= 25
    assert result.grade == "critical"
    assert any("Status punktu: Disabled" in warning for warning in result.warnings)
    assert any("Ocena ograniczona do 25/100" in warning for warning in result.warnings)


def test_created_point_score_is_capped_below_good():
    result = score_point(base_point(status="Created"), requested_functions=[], radius_m=3000)

    assert result.score <= 45
    assert result.grade in {"weak", "critical"}
    assert any("Ocena ograniczona do 45/100" in warning for warning in result.warnings)


def test_no_data_availability_is_warning_not_score_penalty():
    with_no_data = score_point(base_point(), requested_functions=[], radius_m=3000)
    with_unknown = score_point(
        base_point(locker_availability={"status": "AVAILABLE"}),
        requested_functions=[],
        radius_m=3000,
    )

    assert with_no_data.score == with_unknown.score
    assert NO_DATA_WARNING in with_no_data.warnings


def test_missing_requested_function_is_explained():
    result = score_point(base_point(functions=["parcel_collect"]), requested_functions=["parcel_send"], radius_m=3000)

    assert result.score < 90
    assert any("Brak wymaganych akcji" in warning for warning in result.warnings)
