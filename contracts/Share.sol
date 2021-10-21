// SPDX-License-Identifier: MIT
pragma solidity ^0.8.9;
pragma experimental ABIEncoderV2;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

interface VaultAPI is IERC20 {
    function name() external view returns (string calldata);

    function symbol() external view returns (string calldata);

    function decimals() external view returns (uint256);

    function apiVersion() external pure returns (string memory);

    function permit(
        address owner,
        address spender,
        uint256 amount,
        uint256 expiry,
        bytes calldata signature
    ) external returns (bool);

    // NOTE: Vyper produces multiple signatures for a given function with "default" args
    function deposit() external returns (uint256);

    function deposit(uint256 amount) external returns (uint256);

    function deposit(uint256 amount, address recipient) external returns (uint256);

    // NOTE: Vyper produces multiple signatures for a given function with "default" args
    function withdraw() external returns (uint256);

    function withdraw(uint256 maxShares) external returns (uint256);

    function withdraw(uint256 maxShares, address recipient) external returns (uint256);

    function token() external view returns (address);

    function pricePerShare() external view returns (uint256);

    function totalAssets() external view returns (uint256);

    function depositLimit() external view returns (uint256);

    function maxAvailableShares() external view returns (uint256);
}

interface RegistryAPI {
    function governance() external view returns (address);

    function latestVault(address token) external view returns (address);

    function numVaults(address token) external view returns (uint256);

    function vaults(address token, uint256 deploymentId) external view returns (address);
}


contract Share {
    uint256 MAX_DISTRIBUTED = 10_000;
    RegistryAPI public immutable registry;

    struct Beneficiary {
        address account;
        uint16 amount;
    }

    struct Deposit {
        uint256 amount;
        uint256 pricePerShare;
        bool exists;
        Beneficiary[] beneficiaries;
    }

    event Deposited (
        address indexed from,
        address vault,
        uint256 amount
    );

    event Withdrawal(
        address indexed from,
        address vault,
        uint256 amount
    );

    event YieldDistributed(address philanthropist, address vault, uint256 distributed);

    constructor(address _registry) {
        registry = RegistryAPI(_registry);
    }
    
    mapping(address => mapping(address => Deposit)) public deposits;
    mapping(address => mapping(address => uint256)) public claimable;


    function getBeneficiaries(address account, address vault) public view returns(Beneficiary[] memory) {
        return deposits[account][vault].beneficiaries;
    }

    function deposit(address _vault, uint256 amount) public {
        VaultAPI vault = VaultAPI(_vault);
        vault.transferFrom(msg.sender, address(this), amount);
        uint256 pricePerShare = vault.pricePerShare();

        if (deposits[msg.sender][_vault].exists == false) {
            deposits[msg.sender][_vault].amount = amount;
            deposits[msg.sender][_vault].pricePerShare = pricePerShare;
            deposits[msg.sender][_vault].exists = true;
        } else {
            Deposit storage d = deposits[msg.sender][_vault];
            _distributeTokens(msg.sender, d, vault, pricePerShare);
            d.amount += amount;
        }
        emit Deposited(msg.sender, address(vault), amount);
    }

    function depositWant(IERC20 _token, uint256 amount) public {
        SafeERC20.safeTransferFrom(_token, msg.sender, address(this), amount);
        address _vault = registry.latestVault(address(_token));
        VaultAPI vault = VaultAPI(_vault);
        SafeERC20.safeApprove(_token, _vault, amount);
        amount = vault.deposit(amount);

        uint256 pricePerShare = vault.pricePerShare();

        if (deposits[msg.sender][_vault].exists == false) {
            deposits[msg.sender][_vault].amount = amount;
            deposits[msg.sender][_vault].pricePerShare = pricePerShare;
            deposits[msg.sender][_vault].exists = true;
        } else {
            Deposit storage d = deposits[msg.sender][_vault];
            _distributeTokens(msg.sender, d, vault, pricePerShare);
            d.amount += amount;
        }
        emit Deposited(msg.sender, address(vault), amount);
    }

    function withdraw(address _vault, uint256 amount) public {
        withdraw(_vault, amount, true);
    }

    function withdraw(address _vault, uint256 amount, bool distribute) public {
        VaultAPI vault = VaultAPI(_vault);
        Deposit storage d = deposits[msg.sender][_vault];
        if (distribute) { // if _distributeTokens is fucked do not lock tokens.
            uint256 pricePerShare = vault.pricePerShare();
            _distributeTokens(msg.sender, d, vault, pricePerShare);
        }
        
        if (amount >= d.amount) {
            amount = d.amount;
            delete deposits[msg.sender][_vault];
        } else {
            d.amount -= amount;
        }

        vault.transfer(msg.sender, amount);
        emit Withdrawal(msg.sender, address(vault), amount);
    }

    function distributeTokens(address _vault, address account) public {
        VaultAPI vault = VaultAPI(_vault);
        uint256 pricePerShare = vault.pricePerShare();
        Deposit storage d = deposits[account][_vault];

        require(d.exists);
        _distributeTokens(account, d, vault, pricePerShare);

    }

    function distributeTokens(address _vault, address[] calldata accounts) public {
        VaultAPI vault = VaultAPI(_vault);
        uint256 pricePerShare = vault.pricePerShare();

        for(uint256 i= 0; i < accounts.length; i++) {
            Deposit storage d = deposits[accounts[i]][_vault];
            require(d.exists);
            _distributeTokens(accounts[i], d, vault, pricePerShare);
        }
    }

    function _distributeTokens(address philanthropist, Deposit storage d, VaultAPI vault, uint256 pricePerShare) internal returns(bool) {
        if(d.pricePerShare >= pricePerShare) {
            return true;
        }

        uint256 decimalPrecision = 10 ** vault.decimals();
        uint256 increaseInUnderlying = (d.amount * pricePerShare - d.amount * d.pricePerShare) / decimalPrecision;
        uint256 toDecrease = 0;
        if (increaseInUnderlying == 0) {
            return true;
        }

        for(uint256 i=0; i < d.beneficiaries.length; i++) {
            uint256 amountInUnderlying = increaseInUnderlying * d.beneficiaries[i].amount / MAX_DISTRIBUTED;
            uint256 amountInVaultToken = amountInUnderlying * decimalPrecision / pricePerShare;

            claimable[d.beneficiaries[i].account][address(vault)] += amountInVaultToken;
            toDecrease += amountInVaultToken;
        }
        emit YieldDistributed(philanthropist, address(vault), toDecrease);

        d.amount -= toDecrease;
        d.pricePerShare = pricePerShare;
        return true;
    }

    function setBeneficiaries(address _vault, Beneficiary[] calldata _beneficiaries) public {
        Deposit storage d = deposits[msg.sender][_vault];
        require(d.exists, "!exists");
        VaultAPI vault = VaultAPI(_vault);
        uint256 pricePerShare = vault.pricePerShare();
        _distributeTokens(msg.sender, d, vault, pricePerShare);

        delete deposits[msg.sender][_vault].beneficiaries;
        uint256 totalDistributed = 0;
        for(uint256 i = 0; i< _beneficiaries.length; i++) {
            deposits[msg.sender][_vault].beneficiaries.push(_beneficiaries[i]);
            totalDistributed += _beneficiaries[i].amount;
        }
        require(totalDistributed <= MAX_DISTRIBUTED, ">max");
    }

    function claimTokens(address _vault) public {
        uint256 amount = claimable[msg.sender][_vault];
        claimable[msg.sender][_vault] = 0;

        VaultAPI(_vault).transfer(msg.sender, amount);
    }
}
