const Competitor = require('../models/Competitor');
const CompetitorPost = require('../models/CompetitorPost');
const { getOwnedBusinessOrThrow } = require('./business.controller');
const { generateCompetitorPosts } = require('../services/mockAi.service');
const { paginatedResponse } = require('../services/scoring.service');
const asyncHandler = require('../utils/asyncHandler');
const ApiError = require('../utils/ApiError');

const ensureCompetitorAccess = async (userId, competitorId) => {
  const business = await getOwnedBusinessOrThrow(userId);
  const competitor = await Competitor.findOne({ _id: competitorId, businessId: business._id });

  if (!competitor) {
    throw new ApiError(404, 'Competitor not found');
  }

  return { business, competitor };
};

const createCompetitor = asyncHandler(async (req, res) => {
  const business = await getOwnedBusinessOrThrow(req.user._id, req.body.businessId);
  const competitor = await Competitor.create({ ...req.body, businessId: business._id });
  res.status(201).json({ success: true, data: competitor });
});

const listCompetitors = asyncHandler(async (req, res) => {
  const business = await getOwnedBusinessOrThrow(req.user._id);
  const result = await paginatedResponse(
    Competitor,
    { businessId: business._id },
    req.query,
    ['name', 'platform', 'postingFrequency', 'status']
  );

  res.json({ success: true, ...result });
});

const getCompetitor = asyncHandler(async (req, res) => {
  const { competitor } = await ensureCompetitorAccess(req.user._id, req.params.id);
  res.json({ success: true, data: competitor });
});

const updateCompetitor = asyncHandler(async (req, res) => {
  const { competitor } = await ensureCompetitorAccess(req.user._id, req.params.id);
  Object.assign(competitor, req.body);
  await competitor.save();
  res.json({ success: true, data: competitor });
});

const deleteCompetitor = asyncHandler(async (req, res) => {
  const { competitor } = await ensureCompetitorAccess(req.user._id, req.params.id);
  await Promise.all([
    CompetitorPost.deleteMany({ competitorId: competitor._id }),
    competitor.deleteOne()
  ]);

  res.json({ success: true, data: { id: req.params.id } });
});

const listCompetitorPosts = asyncHandler(async (req, res) => {
  const { business, competitor } = await ensureCompetitorAccess(req.user._id, req.params.id);
  const result = await paginatedResponse(
    CompetitorPost,
    { businessId: business._id, competitorId: competitor._id },
    req.query,
    ['caption', 'hook', 'format', 'platform']
  );

  res.json({ success: true, ...result });
});

const mockGenerateCompetitorPosts = asyncHandler(async (req, res) => {
  const { competitor } = await ensureCompetitorAccess(req.user._id, req.params.id);
  const generated = generateCompetitorPosts(competitor, req.body.count || 6);
  const posts = await CompetitorPost.insertMany(generated);

  res.status(201).json({ success: true, data: posts });
});

module.exports = {
  createCompetitor,
  listCompetitors,
  getCompetitor,
  updateCompetitor,
  deleteCompetitor,
  listCompetitorPosts,
  mockGenerateCompetitorPosts
};
