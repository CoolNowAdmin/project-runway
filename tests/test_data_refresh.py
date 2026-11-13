"""The monthly data refresh: download (with a fake data.gov.sg, never the network), build, page figures, workflow."""

import io
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_dataset  # noqa: E402
import refresh_data  # noqa: E402

HEADER = "month,town,flat_type,block,street_name,storey_range,floor_area_sqm,flat_model,lease_commence_date,remaining_lease,resale_price"
ROW = "{m},ANG MO KIO,3 ROOM,406,ANG MO KIO AVE 10,10 TO 12,67,New Generation,1979,{lease},300000"


def fake_data_gov(monkeypatch, csv_for=None, polls_pending=1):
    """Stand in for urlopen: initiate, poll (pending first), then the CSV from a signed link. Records every URL."""
    seen, pending = [], dict.fromkeys(refresh_data.DATASETS.values(), polls_pending)
    csv_for = csv_for or (lambda i: f"{HEADER}\n{ROW.format(m=f'{1990 + i}-01', lease='')}\n")

    def urlopen(req, timeout):
        url = req.full_url
        seen.append(url)
        if url.startswith("https://files.example/"):
            body = csv_for(int(url.rsplit("/", 1)[1])).encode()
        else:
            dataset_id, action = url.split("/")[-2:]
            assert url == refresh_data.API.format(dataset_id, action) and dataset_id in pending
            if action == "poll-download" and pending[dataset_id] > 0:
                pending[dataset_id] -= 1
                body = json.dumps({"code": 0, "data": {"status": "DOWNLOAD_PENDING"}}).encode()
            else:
                i = list(refresh_data.DATASETS.values()).index(dataset_id)
                body = json.dumps({"code": 0, "data": {"status": "DOWNLOAD_SUCCESS", "url": f"https://files.example/{i}"}}).encode()
        return io.BytesIO(body)

    monkeypatch.setattr(refresh_data.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(refresh_data.time, "sleep", lambda s: None)
    return seen


def test_download_writes_five_csvs_that_build_dataset_reads(monkeypatch, tmp_path):
    seen = fake_data_gov(monkeypatch)
    refresh_data.download(tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(refresh_data.DATASETS)
    assert all(u.startswith("https://api-open.data.gov.sg/") or u.startswith("https://files.example/") for u in seen)
    assert sum("poll-download" in u for u in seen) == 10  # one pending poll, then success, per dataset
    df = build_dataset.build(tmp_path)
    assert len(df) == 5
    basis = dict(zip(df["month"].dt.year, df["date_basis"].astype(str)))
    assert basis == {1990: "approval", 1991: "approval", 1992: "registration", 1993: "registration", 1994: "registration"}


def test_an_error_page_never_reaches_the_build(monkeypatch, tmp_path):
    fake_data_gov(monkeypatch, csv_for=lambda i: "<html>Service unavailable</html>")
    with pytest.raises(RuntimeError, match="not the resale CSV"):
        refresh_data.download(tmp_path)
    assert not list(tmp_path.iterdir())


def test_api_error_and_a_download_that_never_gets_ready(monkeypatch):
    monkeypatch.setattr(refresh_data, "fetch", lambda url: b'{"code": 28, "data": null, "errorMsg": "Route not found"}')
    with pytest.raises(RuntimeError, match="Route not found"):
        refresh_data.csv_url("d_x")
    monkeypatch.setattr(refresh_data, "fetch", lambda url: b'{"code": 0, "data": {"status": "DOWNLOAD_PENDING"}}')
    monkeypatch.setattr(refresh_data.time, "sleep", lambda s: None)
    with pytest.raises(RuntimeError, match="not ready"):
        refresh_data.csv_url("d_x", polls=3)


def test_dataset_ids_are_the_five_resale_files():
    assert len(set(refresh_data.DATASETS.values())) == 5
    assert all(i.startswith("d_") and len(i) == 34 for i in refresh_data.DATASETS.values())
    assert [n for n in refresh_data.DATASETS if any(k in n for k in build_dataset.APPROVAL_FILES)] == \
        ["resale-1990-1999.csv", "resale-2000-feb2012.csv"]


def test_page_figures_follow_the_new_data_and_leave_the_map_window(tmp_path):
    page = tmp_path / "index.html"
    shutil.copy(refresh_data.PAGE, page)
    old = json.loads((ROOT / "data" / "dataset_meta.json").read_text())
    before = page.read_text(encoding="utf-8")
    assert all(f in before for f in refresh_data.page_figures(old))
    new = {**old, "rows": 1_000_123, "last_month": "2026-11"}
    refresh_data.update_page(old, new, page)
    after = page.read_text(encoding="utf-8")
    assert all(f in after for f in refresh_data.page_figures(new)) and "986,090" not in after
    assert "<b>1,000,123</b><span>Resale records</span>" in after and "1,000,123 sales from 1990 to Nov 2026" in after
    # the map and its town lease effect come from map.json, which the refresh leaves alone
    assert "Jan 2024 – Sep 2026 sales" in after and "same month (Jan 2024 to Sep 2026)" in after
    assert len(after) - len(before) == 4 * (len("1,000,123") - len("986,090"))  # nothing else moved
    with pytest.raises(RuntimeError, match="no longer says"):
        refresh_data.update_page({**old, "rows": 1}, new, page)


def test_workflow_opens_a_pull_request_and_never_pushes_to_main():
    text = (ROOT / ".github" / "workflows" / "data-refresh.yml").read_text()
    yaml = pytest.importorskip("yaml")
    wf = yaml.safe_load(text)
    on = wf.get("on", wf.get(True))  # YAML 1.1 reads a bare `on` key as True
    assert set(on) == {"schedule", "workflow_dispatch"} and on["schedule"][0]["cron"].split()[2:] == ["3", "*", "*"]
    assert wf["permissions"] == {"contents": "write", "pull-requests": "write"}
    steps = wf["jobs"]["refresh"]["steps"]
    assert {s["uses"].split("@")[0] for s in steps if "uses" in s} == {"actions/checkout", "actions/setup-python"}
    assert next(s for s in steps if "setup-python" in s.get("uses", ""))["with"]["python-version"] == "3.12"
    names = [s.get("name") for s in steps]
    assert names.index("Download and rebuild") < names.index("Test") < names.index("Open a pull request")
    gated = [s for s in steps if s.get("name") in {"Test", "Open a pull request"}]
    assert all(s["if"] == "steps.check.outputs.changed == 'true'" for s in gated)  # nothing happens when the data is the same
    pr = gated[1]
    assert pr["env"] == {"GH_TOKEN": "${{ secrets.GITHUB_TOKEN }}"} and "gh pr create --base main" in pr["run"]
    assert 'git push --force origin "HEAD:refs/heads/$branch"' in pr["run"] and 'branch="data-refresh/' in pr["run"]
    assert "git push origin main" not in text and "refs/heads/main" not in text
