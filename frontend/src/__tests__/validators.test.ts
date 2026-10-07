import { describe, it, expect } from 'vitest';
import {
  loginSchema,
  registerSchema,
  forgotPasswordSchema,
  resetPasswordSchema,
  twoFactorCodeSchema,
  updateProfileSchema,
  deleteAccountSchema,
} from '../utils/validators';

describe('Form Validators & Schemas', () => {
  describe('loginSchema', () => {
    it('accepts valid email and password', () => {
      const result = loginSchema.safeParse({
        email: 'user@example.com',
        password: 'ValidPassword123!',
      });
      expect(result.success).toBe(true);
    });

    it('rejects invalid email formats', () => {
      const result = loginSchema.safeParse({
        email: 'invalid-email',
        password: 'password',
      });
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.errors[0].path).toContain('email');
      }
    });

    it('rejects empty password', () => {
      const result = loginSchema.safeParse({
        email: 'user@example.com',
        password: '',
      });
      expect(result.success).toBe(false);
    });
  });

  describe('registerSchema', () => {
    it('accepts compliant registration payload', () => {
      const result = registerSchema.safeParse({
        name: 'Dr. Tariq',
        email: 'tariq@field.org',
        password: 'SecurePassword1',
        confirmPassword: 'SecurePassword1',
      });
      expect(result.success).toBe(true);
    });

    it('rejects password without uppercase letter', () => {
      const result = registerSchema.safeParse({
        name: 'Dr. Tariq',
        email: 'tariq@field.org',
        password: 'lowercaseonly123',
        confirmPassword: 'lowercaseonly123',
      });
      expect(result.success).toBe(false);
    });

    it('rejects password without digit', () => {
      const result = registerSchema.safeParse({
        name: 'Dr. Tariq',
        email: 'tariq@field.org',
        password: 'NoDigitsPassword',
        confirmPassword: 'NoDigitsPassword',
      });
      expect(result.success).toBe(false);
    });

    it('rejects password shorter than 8 chars', () => {
      const result = registerSchema.safeParse({
        name: 'Dr. Tariq',
        email: 'tariq@field.org',
        password: 'Short1',
        confirmPassword: 'Short1',
      });
      expect(result.success).toBe(false);
    });

    it('rejects mismatched confirm password', () => {
      const result = registerSchema.safeParse({
        name: 'Dr. Tariq',
        email: 'tariq@field.org',
        password: 'ValidPassword1',
        confirmPassword: 'MismatchPassword1',
      });
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.errors[0].message).toContain('Passwords do not match');
      }
    });
  });

  describe('forgotPasswordSchema & resetPasswordSchema', () => {
    it('validates email for forgot password', () => {
      expect(forgotPasswordSchema.safeParse({ email: 'valid@crop.org' }).success).toBe(true);
      expect(forgotPasswordSchema.safeParse({ email: 'bad-email' }).success).toBe(false);
    });

    it('validates password matching on reset', () => {
      const valid = resetPasswordSchema.safeParse({
        new_password: 'NewStrongPassword8',
        confirmPassword: 'NewStrongPassword8',
      });
      expect(valid.success).toBe(true);

      const invalid = resetPasswordSchema.safeParse({
        new_password: 'NewStrongPassword8',
        confirmPassword: 'DiffPassword8',
      });
      expect(invalid.success).toBe(false);
    });
  });

  describe('twoFactorCodeSchema', () => {
    it('accepts 6-digit numeric TOTP codes', () => {
      expect(twoFactorCodeSchema.safeParse({ code: '123456' }).success).toBe(true);
    });

    it('accepts alphanumeric recovery codes', () => {
      expect(twoFactorCodeSchema.safeParse({ code: 'ABCD-EFGH' }).success).toBe(true);
    });

    it('rejects invalid short codes', () => {
      expect(twoFactorCodeSchema.safeParse({ code: '12' }).success).toBe(false);
    });
  });

  describe('updateProfileSchema & deleteAccountSchema', () => {
    it('requires name with minimum length 2', () => {
      expect(updateProfileSchema.safeParse({ name: 'A' }).success).toBe(false);
      expect(updateProfileSchema.safeParse({ name: 'Ali' }).success).toBe(true);
    });

    it('requires explicit DELETE string for account deletion', () => {
      expect(
        deleteAccountSchema.safeParse({
          password: 'SecretPassword1',
          confirmText: 'DELETE',
        }).success
      ).toBe(true);

      expect(
        deleteAccountSchema.safeParse({
          password: 'SecretPassword1',
          confirmText: 'delete',
        }).success
      ).toBe(false);
    });
  });
});
