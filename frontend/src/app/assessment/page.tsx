'use client';

import React from 'react';
import {
  QuestionnaireFlow,
  type QuestionnaireConfig,
} from '@/components/QuestionnaireFlow';
import {
  getQuestions,
  getProgress,
  saveAnswers,
  submitAssessment,
} from '@/lib/api';

const studentAssessmentConfig: QuestionnaireConfig = {
  role: 'student',
  wrongRoleRedirect: '/intake',
  getQuestions,
  getProgress,
  saveAnswers,
  submit: submitAssessment,
  incompleteErrorCode: 'assessment_incomplete',
  reviewType: 'student',
  partnerWaitingTextKey: 'waitingParentDone',
};

export default function StudentAssessmentPage() {
  return <QuestionnaireFlow config={studentAssessmentConfig} />;
}
