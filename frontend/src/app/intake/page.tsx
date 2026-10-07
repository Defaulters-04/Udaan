'use client';

import React from 'react';
import {
  QuestionnaireFlow,
  type QuestionnaireConfig,
} from '@/components/QuestionnaireFlow';
import {
  getIntakeQuestions,
  getIntakeProgress,
  saveIntakeAnswers,
  submitIntake,
} from '@/lib/api';

const parentIntakeConfig: QuestionnaireConfig = {
  role: 'parent',
  wrongRoleRedirect: '/assessment',
  getQuestions: getIntakeQuestions,
  getProgress: getIntakeProgress,
  saveAnswers: saveIntakeAnswers,
  submit: submitIntake,
  incompleteErrorCode: 'intake_incomplete',
  reviewType: 'parent',
  partnerWaitingTextKey: 'waitingStudentDone',
  showPrivacyIntakeOnFirstQuestion: true,
};

export default function ParentIntakePage() {
  return <QuestionnaireFlow config={parentIntakeConfig} />;
}
