"""Object storage provider selection and production fallback safety."""

from __future__ import annotations

from production_platform.production.infrastructure import InfrastructureBundle


def test_production_s3_initialization_failure_does_not_silently_use_memory(
    monkeypatch,
) -> None:
    """Configured S3 must not silently degrade to volatile in-memory storage."""
    from production_platform.adapters import object_storage

    monkeypatch.setattr(
        object_storage,
        "try_build_s3_storage",
        lambda **kwargs: None,
    )

    try:
        InfrastructureBundle.from_environment(
            environ={
                "DSP_ENVIRONMENT": "production",
                "DSP_OBJECT_STORAGE_PROVIDER": "s3",
                "DSP_OBJECT_STORAGE_BUCKET": "test-bucket",
                "DSP_OBJECT_STORAGE_REGION": "ap-south-1",
            }
        )
    except Exception:
        return

    raise AssertionError(
        "Production silently accepted unavailable S3 storage instead of failing"
    )


def test_production_local_storage_requires_root() -> None:
    """Production must reject a missing local storage root."""
    from production_platform.production.exceptions import ConfigurationError

    try:
        InfrastructureBundle.from_environment(
            environ={
                "DSP_ENVIRONMENT": "production",
                "DSP_REGION": "ap-south-1",
                "DSP_OBJECT_STORAGE_PROVIDER": "local",
                "DSP_OBJECT_STORAGE_LOCAL_ROOT": "",
            }
        )
    except ConfigurationError as exc:
        assert "DSP_OBJECT_STORAGE_LOCAL_ROOT" in str(exc)
        return

    raise AssertionError("Production accepted local storage without a root")


def test_staging_rejects_volatile_object_storage() -> None:
    """Staging must not silently accept memory or unsupported providers."""
    from production_platform.production.exceptions import ConfigurationError

    for provider in ("memory", "azure", "gcs"):
        try:
            InfrastructureBundle.from_environment(
                environ={
                    "DSP_ENVIRONMENT": "staging",
                    "DSP_REGION": "ap-south-1",
                    "DSP_OBJECT_STORAGE_PROVIDER": provider,
                }
            )
        except ConfigurationError as exc:
            assert "DSP_OBJECT_STORAGE_PROVIDER" in str(exc)
        else:
            raise AssertionError(
                f"Staging silently accepted object storage provider={provider}"
            )


def test_staging_rejects_missing_object_storage_provider() -> None:
    """The default memory provider must not be accepted in staging."""
    from production_platform.production.exceptions import ConfigurationError

    try:
        InfrastructureBundle.from_environment(
            environ={
                "DSP_ENVIRONMENT": "staging",
                "DSP_REGION": "ap-south-1",
            }
        )
    except ConfigurationError as exc:
        assert "DSP_OBJECT_STORAGE_PROVIDER" in str(exc)
    else:
        raise AssertionError("Staging accepted its implicit memory storage default")


def test_production_rejects_memory_object_storage() -> None:
    """Production must require its explicitly configured persistent provider."""
    from production_platform.production.exceptions import ConfigurationError

    try:
        InfrastructureBundle.from_environment(
            environ={
                "DSP_ENVIRONMENT": "production",
                "DSP_REGION": "ap-south-1",
                "DSP_OBJECT_STORAGE_PROVIDER": "memory",
            }
        )
    except ConfigurationError as exc:
        assert "DSP_OBJECT_STORAGE_PROVIDER" in str(exc)
    else:
        raise AssertionError("Production accepted volatile memory object storage")


def test_development_memory_object_storage_remains_supported() -> None:
    """Development retains its existing in-memory default."""
    infra = InfrastructureBundle.from_environment(
        environ={"DSP_ENVIRONMENT": "development"}
    )
    assert infra.diagnostics.storage_adapter == "InMemoryStoragePort"
