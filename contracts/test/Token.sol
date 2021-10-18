// SPDX-License-Identifier: MIT
pragma solidity ^0.8.9;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract Token is ERC20 {
    mapping(address => bool) public _blocked;

    constructor() ERC20("yearn.finance test token", "TEST") {
    }

    function mint(uint256 amount) public {
        _mint(msg.sender, amount);
    }
}

