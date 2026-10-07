import { z } from 'zod';
import { AUTH_RULES } from './constants';

export const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
  totp_code: z.string().optional(),
  recovery_code: z.string().optional(),
});

export type LoginFormData = z.infer<typeof loginSchema>;

export const registerSchema = z
  .object({
    name: z
      .string()
      .min(
        AUTH_RULES.name.minLength,
        `Full name must be at least ${AUTH_RULES.name.minLength} characters`
      )
      .max(AUTH_RULES.name.maxLength, 'Full name is too long'),
    email: z.string().email('Please enter a valid email address'),
    password: z
      .string()
      .min(
        AUTH_RULES.password.minLength,
        `Password must be at least ${AUTH_RULES.password.minLength} characters`
      )
      .regex(AUTH_RULES.password.regex, AUTH_RULES.password.errorMessage),
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });

export type RegisterFormData = z.infer<typeof registerSchema>;

export const forgotPasswordSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
});

export type ForgotPasswordFormData = z.infer<typeof forgotPasswordSchema>;

export const resetPasswordSchema = z
  .object({
    new_password: z
      .string()
      .min(
        AUTH_RULES.password.minLength,
        `Password must be at least ${AUTH_RULES.password.minLength} characters`
      )
      .regex(AUTH_RULES.password.regex, AUTH_RULES.password.errorMessage),
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.new_password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });

export type ResetPasswordFormData = z.infer<typeof resetPasswordSchema>;

export const twoFactorCodeSchema = z.object({
  code: z
    .string()
    .min(1, 'Code is required')
    .refine((val) => /^\d{6}$/.test(val) || /^[A-Za-z0-9-]{8,12}$/.test(val), {
      message: 'Enter a valid 6-digit TOTP code or recovery code',
    }),
});

export type TwoFactorCodeFormData = z.infer<typeof twoFactorCodeSchema>;

export const updateProfileSchema = z.object({
  name: z
    .string()
    .min(
      AUTH_RULES.name.minLength,
      `Full name must be at least ${AUTH_RULES.name.minLength} characters`
    )
    .max(AUTH_RULES.name.maxLength, 'Full name is too long'),
});

export type UpdateProfileFormData = z.infer<typeof updateProfileSchema>;

export const changeEmailSchema = z.object({
  new_email: z.string().email('Please enter a valid email address'),
  password: z.string().min(1, 'Password is required to confirm change'),
});

export type ChangeEmailFormData = z.infer<typeof changeEmailSchema>;

export const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, 'Current password is required'),
    new_password: z
      .string()
      .min(
        AUTH_RULES.password.minLength,
        `Password must be at least ${AUTH_RULES.password.minLength} characters`
      )
      .regex(AUTH_RULES.password.regex, AUTH_RULES.password.errorMessage),
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.new_password === data.confirmPassword, {
    message: 'New passwords do not match',
    path: ['confirmPassword'],
  });

export type ChangePasswordFormData = z.infer<typeof changePasswordSchema>;

export const deleteAccountSchema = z.object({
  password: z.string().min(1, 'Password is required to confirm deletion'),
  confirmText: z.literal('DELETE', {
    errorMap: () => ({ message: 'Please type DELETE to confirm' }),
  }),
});

export type DeleteAccountFormData = z.infer<typeof deleteAccountSchema>;
