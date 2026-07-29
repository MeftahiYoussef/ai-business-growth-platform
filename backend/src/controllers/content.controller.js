const ContentIdea = require('../models/ContentIdea');
const Trend = require('../models/Trend');
const { getOwnedBusinessOrThrow } = require('./business.controller');
const { generateContentIdeas } = require('../services/mockAi.service');
const { paginatedResponse } = require('../services/scoring.service');
const asyncHandler = require('../utils/asyncHandler');
const ApiError = require('../utils/ApiError');

const listContentIdeas = asyncHandler(async (req, res) => {
  const business = await getOwnedBusinessOrThrow(req.user._id);
  const result = await paginatedResponse(
    ContentIdea,
    { businessId: business._id },
    req.query,
    ['title', 'hook', 'caption', 'format', 'status', 'reason']
  );

  res.json({ success: true, ...result });
});

const generateIdeas = asyncHandler(async (req, res) => {
  const business = await getOwnedBusinessOrThrow(req.user._id, req.body.businessId);
  const trends = await Trend.find({ businessId: business._id }).sort({ createdAt: -1 }).limit(5);
  const generated = generateContentIdeas(business, trends, req.body.count || 10);
  const ideas = await ContentIdea.insertMany(generated);

  res.status(201).json({ success: true, data: ideas });
});

const saveIdea = asyncHandler(async (req, res) => {
  const business = await getOwnedBusinessOrThrow(req.user._id);
  const idea = await ContentIdea.findOneAndUpdate(
    { _id: req.params.id, businessId: business._id },
    { status: 'saved' },
    { new: true }
  );

  if (!idea) {
    throw new ApiError(404, 'Content idea not found');
  }

  res.json({ success: true, data: idea });
});

const deleteIdea = asyncHandler(async (req, res) => {
  const business = await getOwnedBusinessOrThrow(req.user._id);
  const idea = await ContentIdea.findOneAndDelete({
    _id: req.params.id,
    businessId: business._id
  });

  if (!idea) {
    throw new ApiError(404, 'Content idea not found');
  }

  res.json({ success: true, data: { id: req.params.id } });
});

module.exports = {
  listContentIdeas,
  generateIdeas,
  saveIdea,
  deleteIdea
};
