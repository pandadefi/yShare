import pytest
import brownie

MAX_UINT256 = 2 ** 256 - 1


def test_deposit(token, vault, share, deployer):
    amount = 10_000 * 10 ** 18
    token.mint(amount * 100, {"from": deployer})
    token.approve(vault, MAX_UINT256, {"from": deployer})
    vault.deposit(amount, {"from": deployer})
    vault.approve(share, MAX_UINT256, {"from": deployer})
    share.deposit(vault, amount, {"from": deployer})
    assert token.balanceOf(vault) == amount
    assert vault.balanceOf(share) == amount

    token.mint(amount / 10, {"from": vault})  # increase price per share
    vault.deposit(amount, {"from": deployer})
    balance = vault.balanceOf(deployer)
    assert pytest.approx(balance) == amount / 1.1
    share.deposit(vault, balance, {"from": deployer})
    assert (
        pytest.approx(share.deposits(deployer, vault).dict()["amount"])
        == amount + amount / 1.1
    )
    assert (
        share.deposits(deployer, vault).dict()["pricePerShare"] == 1100000000000000000
    )


def test_deposit_want(token, vault, share, deployer, registry):
    amount = 10_000 * 10 ** 18
    token.mint(amount * 100, {"from": deployer})
    token.approve(share, MAX_UINT256, {"from": deployer})
    registry.newRelease(vault, {"from": deployer})
    registry.endorseVault(vault, {"from": deployer})
    share.depositWant(token, amount, {"from": deployer})
    assert token.balanceOf(vault) == amount
    assert vault.balanceOf(share) == amount

    token.mint(amount / 10, {"from": vault})  # increase price per share
    share.depositWant(token, amount, {"from": deployer})
    assert (
        pytest.approx(share.deposits(deployer, vault).dict()["amount"])
        == amount + amount / 1.1
    )
    assert (
        share.deposits(deployer, vault).dict()["pricePerShare"] == 1100000000000000000
    )
    assert pytest.approx(vault.balanceOf(share)) == amount + amount / 1.1


def test_add_beneficiaries(token, vault, share, deployer, user, user2):
    amount = 10_000 * 10 ** 18
    token.mint(amount * 100, {"from": deployer})
    token.approve(vault, MAX_UINT256, {"from": deployer})
    vault.deposit(amount, {"from": deployer})
    vault.approve(share, MAX_UINT256, {"from": deployer})
    share.deposit(vault, amount, {"from": deployer})

    share.setBeneficiaries(vault, [(user, 1000), (user2, 100)], {"from": deployer})
    assert share.getBeneficiaries(deployer, vault)[0][0] == user
    assert share.getBeneficiaries(deployer, vault)[0][1] == 1000
    assert share.getBeneficiaries(deployer, vault)[1][0] == user2
    assert share.getBeneficiaries(deployer, vault)[1][1] == 100

    with brownie.reverts():
        share.setBeneficiaries(
            vault, [(user, 10_000), (user2, 100)], {"from": deployer}
        )


def test_deposit_add_beneficiaries_claim(token, vault, share, deployer, user, user2):
    amount = 10_000 * 10 ** 18
    token.mint(amount, {"from": deployer})
    token.approve(vault, MAX_UINT256, {"from": deployer})
    vault.deposit(amount, {"from": deployer})
    vault.approve(share, MAX_UINT256, {"from": deployer})
    share.deposit(vault, amount, {"from": deployer})

    assert token.balanceOf(vault) == amount
    assert vault.balanceOf(share) == amount
    assert share.claimable(user, vault) == 0

    share.setBeneficiaries(
        vault, [(user, 4000), (user2, 1000)], {"from": deployer}
    )  # give 50% of yield
    token.mint(amount / 10, {"from": vault})  # increase price per share
    share.distributeTokens(vault, deployer)
    deposit = share.deposits(deployer, vault).dict()
    assert deposit["pricePerShare"] == 1100000000000000000
    assert pytest.approx(deposit["amount"], rel=10e-4) == 9545 * 10 ** 18
    assert pytest.approx(share.claimable(user, vault), rel=10e-4) == 3636 * 10 ** 17
    assert pytest.approx(share.claimable(user2, vault), rel=10e-4) == 9090 * 10 ** 16

    share.claimTokens(vault, {"from": user})
    share.claimTokens(vault, {"from": user2})
    share.withdraw(vault, deposit["amount"], {"from": deployer})

    vault.withdraw({"from": user})
    vault.withdraw({"from": user2})
    vault.withdraw({"from": deployer})

    assert pytest.approx(token.balanceOf(user)) == 40 * 10 ** 19
    assert pytest.approx(token.balanceOf(user2)) == 10 * 10 ** 19
    assert pytest.approx(token.balanceOf(deployer)) == amount + amount / 20


def test_deposit_add_beneficiaries_claim(token, vault, share, deployer, user, user2):
    amount = 10_000 * 10 ** 18
    token.mint(amount, {"from": deployer})
    token.approve(vault, MAX_UINT256, {"from": deployer})
    vault.deposit(amount, {"from": deployer})
    vault.approve(share, MAX_UINT256, {"from": deployer})
    share.deposit(vault, amount, {"from": deployer})

    assert token.balanceOf(vault) == amount
    assert vault.balanceOf(share) == amount
    assert share.claimable(user, vault) == 0

    share.setBeneficiaries(
        vault, [(user, 9000), (user2, 1000)], {"from": deployer}
    )  # give 100% of yield
    token.mint(amount / 20, {"from": vault})  # increase price per share
    share.distributeTokens["address,address"](vault, deployer)
    deposit = share.deposits(deployer, vault).dict()

    assert deposit["pricePerShare"] == 1050000000000000000
    assert pytest.approx(deposit["amount"], rel=10e-3) == 95 * 10 ** 20

    share.claimTokens(vault, {"from": user})
    share.claimTokens(vault, {"from": user2})
    share.withdraw(vault, deposit["amount"], {"from": deployer})

    vault.withdraw({"from": user})
    vault.withdraw({"from": user2})
    vault.withdraw({"from": deployer})

    assert pytest.approx(token.balanceOf(user), rel=10e-3) == 45 * 10 ** 19
    assert pytest.approx(token.balanceOf(user2), rel=10e-3) == 5 * 10 ** 19
    assert pytest.approx(token.balanceOf(deployer), rel=10e-18) == amount


def test_deposit_add_beneficiaries_claim_mulitple_deposits(
    token, vault, share, deployer, user, user2, user3
):
    amount = 10_000 * 10 ** 18
    # deposit from deployer
    token.mint(amount, {"from": deployer})
    token.approve(vault, MAX_UINT256, {"from": deployer})
    vault.deposit(amount, {"from": deployer})
    vault.approve(share, MAX_UINT256, {"from": deployer})
    share.deposit(vault, amount, {"from": deployer})

    # deposit from user3
    token.mint(amount, {"from": user3})
    token.approve(vault, MAX_UINT256, {"from": user3})
    vault.deposit(amount, {"from": user3})
    vault.approve(share, MAX_UINT256, {"from": user3})
    share.deposit(vault, amount, {"from": user3})

    share.setBeneficiaries(vault, [(user, 4500), (user2, 500)], {"from": deployer})
    share.setBeneficiaries(vault, [(user, 4500), (user2, 500)], {"from": user3})

    token.mint(amount / 10, {"from": vault})  # increase price per share
    share.distributeTokens["address,address[]"](vault, [deployer, user3])
    deposit = share.deposits(deployer, vault).dict()

    assert deposit["pricePerShare"] == 1050000000000000000
    assert pytest.approx(deposit["amount"], rel=10e-3) == 97.5 * 10 ** 20

    share.claimTokens(vault, {"from": user})
    share.claimTokens(vault, {"from": user2})
    share.withdraw(vault, deposit["amount"], {"from": deployer})
    share.withdraw(vault, deposit["amount"], {"from": user3})

    vault.withdraw({"from": user})
    vault.withdraw({"from": user2})
    vault.withdraw({"from": deployer})
    vault.withdraw({"from": user3})

    assert pytest.approx(token.balanceOf(user), rel=10e-3) == 45 * 10 ** 19
    assert pytest.approx(token.balanceOf(user2), rel=10e-3) == 5 * 10 ** 19
    assert pytest.approx(token.balanceOf(deployer), rel=10e-18) == amount * 1.025
    assert pytest.approx(token.balanceOf(user3), rel=10e-18) == amount * 1.025


def test_change_beneficiaries(
    token, vault, share, deployer, user, user2
):
    amount = 10_000 * 10 ** 18
    # deposit from deployer
    token.mint(amount, {"from": deployer})
    token.approve(vault, MAX_UINT256, {"from": deployer})
    vault.deposit(amount, {"from": deployer})
    vault.approve(share, MAX_UINT256, {"from": deployer})
    share.deposit(vault, amount, {"from": deployer})

    share.setBeneficiaries(vault, [(user, 4500), (user2, 500)], {"from": deployer})
    beneficiaries = share.getBeneficiaries(deployer, vault)
    assert beneficiaries[0][0] == user
    assert beneficiaries[0][1] == 4500
    assert beneficiaries[1][0] == user2
    assert beneficiaries[1][1] == 500

    beneficiaries = share.setBeneficiaries(vault, [(user, 500)], {"from": deployer})
    beneficiaries = share.getBeneficiaries(deployer, vault)
    assert beneficiaries[0][0] == user
    assert beneficiaries[0][1] == 500
