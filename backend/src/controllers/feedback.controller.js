const Feedback = require('../models/Feedback');
const ContentIdea = require('../models/ContentIdea');
const { getOwnedBusinessOrThrow } = require('./business.controller');
const asyncHandler = require('../utils/asyncHandler');
const ApiError = require('../utils/ApiError');

const createFeedback = asyncHandler(async (req, res) => {
  const business = await getOwnedBusinessOrThrow(req.user._id, req.body.businessId);
  const idea = await ContentIdea.findOne({
    _id: req.body.contentIdeaId,
    businessId: business._id
  });

  if (!idea) {
    throw new ApiError(404, 'Content idea not found');
  }

  const feedback = await Feedback.create({
    businessId: business._id,
    contentIdeaId: idea._id,
    liked: req.body.liked,
    comment: req.body.comment || ''
  });

  res.status(201).json({ success: true, data: feedback });
});

module.exports = { createFeedback };
