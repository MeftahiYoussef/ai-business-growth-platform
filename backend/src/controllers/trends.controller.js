const Trend = require('../models/Trend');
const CompetitorPost = require('../models/CompetitorPost');
const { getOwnedBusinessOrThrow } = require('./business.controller');
const { generateTrends } = require('../services/mockAi.service');
const { paginatedResponse } = require('../services/scoring.service');
const asyncHandler = require('../utils/asyncHandler');

const listTrends = asyncHandler(async (req, res) => {
  const business = await getOwnedBusinessOrThrow(req.user._id);
  const result = await paginatedResponse(
    Trend,
    { businessId: business._id },
    req.query,
    ['topic', 'format', 'momentumLabel', 'explanation']
  );

  res.json({ success: true, ...result });
});

const analyzeTrends = asyncHandler(async (req, res) => {
  const business = await getOwnedBusinessOrThrow(req.user._id, req.body.businessId);
  const sourcePosts = await CompetitorPost.find({ businessId: business._id }).limit(10);
  const generated = generateTrends(business, sourcePosts);
  const trends = await Trend.insertMany(generated);

  res.status(201).json({ success: true, data: trends });
});

module.exports = { listTrends, analyzeTrends };
