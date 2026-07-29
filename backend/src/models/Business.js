const mongoose = require('mongoose');

const businessSchema = new mongoose.Schema(
  {
    ownerId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: true,
      index: true
    },
    name: {
      type: String,
      required: true,
      trim: true
    },
    industry: {
      type: String,
      required: true,
      trim: true
    },
    country: {
      type: String,
      required: true,
      trim: true
    },
    productOrService: {
      type: String,
      required: true,
      trim: true
    },
    targetAudience: {
      type: String,
      required: true,
      trim: true
    },
    goals: {
      type: [String],
      default: []
    },
    knownCompetitors: {
      type: [String],
      default: []
    },
    brandVoice: {
      type: String,
      default: 'Clear, confident, and helpful'
    }
  },
  { timestamps: true }
);

module.exports = mongoose.model('Business', businessSchema);
