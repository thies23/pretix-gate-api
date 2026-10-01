from setuptools import setup, find_packages


setup(
    name="pretix-gate-api",
    version="0.0.1",
    description="Custom API for managing pretix device gate assignments",
    author="Thies Mueller",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pretix>=2026.1",
    ],
    entry_points={
        "pretix.plugin": [
            "pretix_gate_api=pretix_gate_api:PretixPluginMeta",
        ],
    },
)