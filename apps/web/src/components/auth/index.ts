export { AuthCard, AuthShell } from "./AuthShell";
export { PasswordStrengthMeter } from "./PasswordStrength";
export {
  evaluatePasswordStrength,
  isPlausibleLoginIdentifier,
  isValidEmail,
  mapAuthError,
  normalizeIndiaMobileInput,
  normalizeLoginIdentifier,
  suggestedUsernameFromMobile,
  type PasswordStrength,
} from "./authValidation";
export { ProviderButton, type ProviderButtonProps } from "./ProviderButton";
export {
  EmailLinkIcon,
  FacebookIcon,
  GoogleIcon,
  MicrosoftIcon,
  MobileIcon,
  PasskeyIcon,
  ProviderIcon,
} from "./ProviderIcons";
export { OtpInput, type OtpInputProps } from "./OtpInput";
export { ResendCountdown } from "./ResendCountdown";
export { PasskeyButton, type PasskeyButtonProps } from "./PasskeyButton";
export { MfaChallenge, type MfaChallengeProps } from "./MfaChallenge";
