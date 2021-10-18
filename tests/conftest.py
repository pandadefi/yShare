import pytest
from brownie import config
from brownie import Contract
from brownie import Token


@pytest.fixture
def gov(accounts):
    yield accounts.at("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52", force=True)


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
def vault(pm, gov, rewards, deployer, management, token):
    Vault = pm(config["dependencies"][0]).Vault
    vault = deployer.deploy(Vault)
    vault.initialize(token, gov, rewards, "", "", deployer, management)
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    vault.setManagement(management, {"from": gov})
    yield vault


@pytest.fixture
def share(deployer, Share):
    yield deployer.deploy(Share)
