const Strategy = require('../models/Strategy');
const Trend = require('../models/Trend');
const { getOwnedBusinessOrThrow } = require('./business.controller');
const { generateStrategy } = require('../services/mockAi.service');
const asyncHandler = require('../utils/asyncHandler');

const getStrategy = asyncHandler(async (req, res) => {
  const business = await getOwnedBusinessOrThrow(req.user._id);
  const strategy = await Strategy.findOne({ businessId: business._id }).sort({ createdAt: -1 });

  res.json({ success: true, data: strategy });
});

const generateBusinessStrategy = asyncHandler(async (req, res) => {
  const business = await getOwnedBusinessOrThrow(req.user._id, req.body.businessId);
  const trends = await Trend.find({ businessId: business._id }).sort({ createdAt: -1 }).limit(5);
  const strategy = await Strategy.create(generateStrategy(business, trends));

  res.status(201).json({ success: true, data: strategy });
});

module.exports = { getStrategy, generateBusinessStrategy };
