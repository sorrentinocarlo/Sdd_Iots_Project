var Contract = artifacts.require("AttendanceTracker");

module.exports = function(deployer) {
  deployer.deploy(Contract);
};