import pytest
from brownie import config
from brownie import Contract
from brownie import Token


@pytest.fixture
def deployer(accounts):
    yield accounts[0]


@pytest.fixture
def rewards(accounts):
    yield accounts[1]


@pytest.fixture
def management(accounts):
    yield accounts[2]


@pytest.fixture
def user(accounts):
    yield accounts[3]


@pytest.fixture
def user2(accounts):
    yield accounts[4]


@pytest.fixture
def user3(accounts):
    yield accounts[5]


@pytest.fixture
def token(Token, deployer):
    yield deployer.deploy(Token)


@pytest.fixture
def registry(pm, deployer):
    Registry = pm(config["dependencies"][0]).Registry
    registry = deployer.deploy(Registry)
    yield registry


@pytest.fixture
def vault(pm, rewards, deployer, management, token):
    Vault = pm(config["dependencies"][0]).Vault
    vault = deployer.deploy(Vault)
    vault.initialize(token, deployer, rewards, "", "", deployer, management)
    vault.setDepositLimit(2 ** 256 - 1, {"from": deployer})
    vault.setManagement(management, {"from": deployer})
    yield vault


@pytest.fixture
def share(deployer, registry, Share):
    yield deployer.deploy(Share, registry)
