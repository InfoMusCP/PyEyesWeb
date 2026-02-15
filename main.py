import toml


def define_env(env):
    try:
        # Load pyproject.toml
        with open("pyproject.toml", "r") as f:
            data = toml.load(f)

        # This example attempts to find it in [project] first, then falls back to [tool.poetry]
        version = data.get("project", {}).get("version")
        print(version)

        env.conf['extra']['version'] = version
        print(env.variables.project_version)
    except Exception as e:
        print(f"Error loading version from pyproject.toml: {e}")
        env.variables.project_version = "Error"