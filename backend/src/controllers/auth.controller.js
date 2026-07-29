const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const User = require('../models/User');
const asyncHandler = require('../utils/asyncHandler');
const ApiError = require('../utils/ApiError');

const signToken = (user) => {
  return jwt.sign(
    { id: user._id, role: user.role },
    process.env.JWT_SECRET,
    { expiresIn: process.env.JWT_EXPIRES_IN || '7d' }
  );
};

const sanitizeUser = (user) => ({
  id: user._id,
  fullName: user.fullName,
  email: user.email,
  role: user.role,
  createdAt: user.createdAt,
  updatedAt: user.updatedAt
});

const register = asyncHandler(async (req, res) => {
  const { fullName, email, password, role = 'owner' } = req.body;
  const existing = await User.findOne({ email });

  if (existing) {
    throw new ApiError(409, 'Email is already registered');
  }

  const passwordHash = await bcrypt.hash(password, 12);
  const user = await User.create({ fullName, email, passwordHash, role });
  const token = signToken(user);

  res.status(201).json({ success: true, token, data: sanitizeUser(user) });
});

const login = asyncHandler(async (req, res) => {
  const { email, password } = req.body;
  const user = await User.findOne({ email });

  if (!user) {
    throw new ApiError(401, 'Invalid email or password');
  }

  const passwordMatches = await bcrypt.compare(password, user.passwordHash);

  if (!passwordMatches) {
    throw new ApiError(401, 'Invalid email or password');
  }

  const token = signToken(user);
  res.json({ success: true, token, data: sanitizeUser(user) });
});

const me = asyncHandler(async (req, res) => {
  res.json({ success: true, data: sanitizeUser(req.user) });
});

module.exports = { register, login, me };
