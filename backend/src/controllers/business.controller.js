const Business = require('../models/Business');
const asyncHandler = require('../utils/asyncHandler');
const ApiError = require('../utils/ApiError');

const createBusiness = asyncHandler(async (req, res) => {
  const business = await Business.create({
    ...req.body,
    ownerId: req.user._id
  });

  res.status(201).json({ success: true, data: business });
});

const getMyBusiness = asyncHandler(async (req, res) => {
  const business = await Business.findOne({ ownerId: req.user._id });
  res.json({ success: true, data: business });
});

const updateBusiness = asyncHandler(async (req, res) => {
  const business = await Business.findOneAndUpdate(
    { _id: req.params.id, ownerId: req.user._id },
    req.body,
    { new: true, runValidators: true }
  );

  if (!business) {
    throw new ApiError(404, 'Business not found');
  }

  res.json({ success: true, data: business });
});

const getOwnedBusinessOrThrow = async (userId, businessId = null) => {
  const filter = businessId ? { _id: businessId, ownerId: userId } : { ownerId: userId };
  const business = await Business.findOne(filter);

  if (!business) {
    throw new ApiError(404, 'Business not found for this user');
  }

  return business;
};

module.exports = {
  createBusiness,
  getMyBusiness,
  updateBusiness,
  getOwnedBusinessOrThrow
};
