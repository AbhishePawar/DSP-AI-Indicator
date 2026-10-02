                "read_only",
                name="Read Only Viewer",
                permissions=["read_research"],
            )
        if self.auth.roles.get("viewer") is None:
            self.auth.roles.upsert(
                "viewer",
                name="Viewer",
                permissions=["read_research"],
            )
        if self.auth.roles.get("enterprise_client") is None:
            self.auth.roles.upsert(
                "enterprise_client",
                name="Enterprise Client",
                permissions=["read_research"],
            )

    def ensure_dev_admin_seed(self) -> None:
        """Seed the development admin only when an explicit fixture password is configured."""
        users = self.auth.users.list_users()
        if any("super_admin" in u.roles or "administrator" in u.roles for u in users):
            return
        env = (os.environ.get("DSP_ENVIRONMENT") or "development").lower()
        if (
            env in {"production", "prod"}
            and os.environ.get("DSP_FORCE_ADMIN_SEED") != "1"
        ):
            return
        password = os.environ.get("DSP_SEED_ADMIN_PASSWORD") or os.environ.get("DSP_P109_PASSWORD")
        if not password:
            raise RuntimeError(
                "Development admin seed requires DSP_SEED_ADMIN_PASSWORD; "
                "configure the local fixture credential instead of using a default password."
            )
        meta = freeze_mapping(
            {
                "auth_entity": "user",
                "provider": AuthProvider.EMAIL.value,
                "email_verified": True,
                "phone_verified": False,
                "seeded": True,
            }
        )
        try:
            user = self.auth.users.create(
                username="admin",
                email="admin@dspai.local",
                password=password,
                display_name="Administrator",
                roles=["administrator"],
                user_id="seed-admin",
            )
        except DuplicateUserError:
            return
        enriched = AuthUser(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            password_hash=user.password_hash,
            status=user.status,