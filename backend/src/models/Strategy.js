const mongoose = require('mongoose');

const strategySchema = new mongoose.Schema(
  {
    businessId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Business',
      required: true,
      index: true
    },
    weeklyCalendar: {
      type: [mongoose.Schema.Types.Mixed],
      default: []
    },
    bestPostingTimes: {
      type: [String],
      default: []
    },
    recommendedHashtags: {
      type: [String],
      default: []
    },
    targetAudienceRecommendation: {
      type: String,
      default: ''
    },
    nextBestActions: {
      type: [mongoose.Schema.Types.Mixed],
      default: []
    }
  },
  { timestamps: { createdAt: true, updatedAt: false } }
);

module.exports = mongoose.model('Strategy', strategySchema);
