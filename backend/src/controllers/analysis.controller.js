const BusinessAnalysis = require('../models/BusinessAnalysis');
const Trend = require('../models/Trend');
const { getOwnedBusinessOrThrow } = require('./business.controller');
const { generateBusinessAnalysis } = require('../services/mockAi.service');
const asyncHandler = require('../utils/asyncHandler');

const getAnalysis = asyncHandler(async (req, res) => {
  const business = await getOwnedBusinessOrThrow(req.user._id);
  const analysis = await BusinessAnalysis.findOne({ businessId: business._id }).sort({ createdAt: -1 });

  res.json({ success: true, data: analysis });
});

const generateAnalysis = asyncHandler(async (req, res) => {
  const business = await getOwnedBusinessOrThrow(req.user._id, req.body.businessId);
  const trends = await Trend.find({ businessId: business._id }).sort({ createdAt: -1 }).limit(5);
  const analysis = await BusinessAnalysis.create(generateBusinessAnalysis(business, trends));

  res.status(201).json({ success: true, data: analysis });
});

module.exports = { getAnalysis, generateAnalysis };
