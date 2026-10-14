"""
The s3 connector against moto's in-process AWS: buckets, puts, gets,
listings, and deletes through the async surface.
"""

import asyncio

import pytest

moto = pytest.importorskip("moto")

from plyght.connectors import S3Connector


@pytest.fixture
def aws(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    with moto.mock_aws():
        yield


def test_round_trip(aws):
    async def run():
        async with S3Connector() as s3:
            assert await s3.healthy()
            await s3.ensure_bucket("artifacts")
            await s3.ensure_bucket("artifacts")
            await s3.put("artifacts", "runs/1.json", b"{}")
            data = await s3.get("artifacts", "runs/1.json")
            listed = await s3.list("artifacts", prefix="runs/")
            await s3.delete("artifacts", "runs/1.json")
            return data, listed, await s3.list("artifacts")

    data, listed, after = asyncio.run(run())
    assert data == b"{}"
    assert [entry["key"] for entry in listed] == ["runs/1.json"]
    assert after == []
