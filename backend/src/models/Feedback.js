const mongoose = require('mongoose');

const feedbackSchema = new mongoose.Schema(
  {
    businessId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Business',
      required: true,
      index: true
    },
    contentIdeaId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'ContentIdea',
      required: true
    },
    liked: {
      type: Boolean,
      required: true
    },
    comment: {
      type: String,
      default: ''
    }
  },
  { timestamps: { createdAt: true, updatedAt: false } }
);

module.exports = mongoose.model('Feedback', feedbackSchema);
