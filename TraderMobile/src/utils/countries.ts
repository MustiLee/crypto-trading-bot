export interface Country {
  code: string;
  name: string;
  phoneCode: string;
  phoneLength: number;
  flag: string;
  phoneFormat?: string;
}

export const countries: Country[] = [
  {
    code: 'TR',
    name: 'Türkiye',
    phoneCode: '+90',
    phoneLength: 10,
    flag: '🇹🇷',
    phoneFormat: '(XXX) XXX XX XX'
  },
  {
    code: 'US',
    name: 'United States',
    phoneCode: '+1',
    phoneLength: 10,
    flag: '🇺🇸',
    phoneFormat: '(XXX) XXX-XXXX'
  },
  {
    code: 'GB',
    name: 'United Kingdom',
    phoneCode: '+44',
    phoneLength: 10,
    flag: '🇬🇧',
    phoneFormat: 'XXXX XXX XXXX'
  },
  {
    code: 'DE',
    name: 'Germany',
    phoneCode: '+49',
    phoneLength: 11,
    flag: '🇩🇪',
    phoneFormat: 'XXX XXXX XXXX'
  },
  {
    code: 'FR',
    name: 'France',
    phoneCode: '+33',
    phoneLength: 9,
    flag: '🇫🇷',
    phoneFormat: 'X XX XX XX XX'
  },
  {
    code: 'ES',
    name: 'Spain',
    phoneCode: '+34',
    phoneLength: 9,
    flag: '🇪🇸',
    phoneFormat: 'XXX XX XX XX'
  },
  {
    code: 'IT',
    name: 'Italy',
    phoneCode: '+39',
    phoneLength: 10,
    flag: '🇮🇹',
    phoneFormat: 'XXX XXX XXXX'
  },
  {
    code: 'NL',
    name: 'Netherlands',
    phoneCode: '+31',
    phoneLength: 9,
    flag: '🇳🇱',
    phoneFormat: 'X XXXX XXXX'
  },
  {
    code: 'CA',
    name: 'Canada',
    phoneCode: '+1',
    phoneLength: 10,
    flag: '🇨🇦',
    phoneFormat: '(XXX) XXX-XXXX'
  },
  {
    code: 'AU',
    name: 'Australia',
    phoneCode: '+61',
    phoneLength: 9,
    flag: '🇦🇺',
    phoneFormat: 'XXX XXX XXX'
  },
  {
    code: 'JP',
    name: 'Japan',
    phoneCode: '+81',
    phoneLength: 10,
    flag: '🇯🇵',
    phoneFormat: 'XX XXXX XXXX'
  },
  {
    code: 'KR',
    name: 'South Korea',
    phoneCode: '+82',
    phoneLength: 10,
    flag: '🇰🇷',
    phoneFormat: 'XX XXXX XXXX'
  },
  {
    code: 'CN',
    name: 'China',
    phoneCode: '+86',
    phoneLength: 11,
    flag: '🇨🇳',
    phoneFormat: 'XXX XXXX XXXX'
  },
  {
    code: 'IN',
    name: 'India',
    phoneCode: '+91',
    phoneLength: 10,
    flag: '🇮🇳',
    phoneFormat: 'XXXXX XXXXX'
  },
  {
    code: 'BR',
    name: 'Brazil',
    phoneCode: '+55',
    phoneLength: 11,
    flag: '🇧🇷',
    phoneFormat: 'XX XXXXX XXXX'
  },
  {
    code: 'MX',
    name: 'Mexico',
    phoneCode: '+52',
    phoneLength: 10,
    flag: '🇲🇽',
    phoneFormat: 'XXX XXX XXXX'
  },
  {
    code: 'RU',
    name: 'Russia',
    phoneCode: '+7',
    phoneLength: 10,
    flag: '🇷🇺',
    phoneFormat: 'XXX XXX XX XX'
  },
  {
    code: 'AE',
    name: 'United Arab Emirates',
    phoneCode: '+971',
    phoneLength: 9,
    flag: '🇦🇪',
    phoneFormat: 'XX XXX XXXX'
  },
  {
    code: 'SA',
    name: 'Saudi Arabia',
    phoneCode: '+966',
    phoneLength: 9,
    flag: '🇸🇦',
    phoneFormat: 'XX XXX XXXX'
  },
  {
    code: 'EG',
    name: 'Egypt',
    phoneCode: '+20',
    phoneLength: 10,
    flag: '🇪🇬',
    phoneFormat: 'XXX XXX XXXX'
  }
];

export const validatePhoneNumber = (phone: string, country: Country): boolean => {
  // Remove all non-digit characters
  const cleanPhone = phone.replace(/\D/g, '');
  
  // Check if length matches the expected length for the country
  if (cleanPhone.length !== country.phoneLength) {
    return false;
  }
  
  // Country-specific validations
  switch (country.code) {
    case 'TR':
      // Turkish mobile numbers start with 5
      return cleanPhone.startsWith('5');
    case 'US':
    case 'CA':
      // US/Canada: Area code can't start with 0 or 1
      return !cleanPhone.startsWith('0') && !cleanPhone.startsWith('1');
    case 'GB':
      // UK mobile numbers typically start with 7
      return cleanPhone.startsWith('7');
    default:
      return true;
  }
};

export const formatPhoneNumber = (phone: string, country: Country): string => {
  // Only keep digits
  const cleanPhone = phone.replace(/\D/g, '');
  
  // If no format specified, return digits only
  if (!country.phoneFormat) {
    return cleanPhone;
  }
  
  // Don't format if empty
  if (cleanPhone.length === 0) {
    return '';
  }
  
  // Apply formatting only up to the available digits
  let formatted = '';
  let phoneIndex = 0;
  
  for (let i = 0; i < country.phoneFormat.length && phoneIndex < cleanPhone.length; i++) {
    const ch = country.phoneFormat[i];
    if (ch === 'X') {
      formatted += cleanPhone[phoneIndex];
      phoneIndex++;
    } else if (!/[0-9]/.test(ch)) {
      // Only inject non-digit formatting characters (spaces, dashes, parentheses)
      formatted += ch;
    } else {
      // Skip literal digits in format to avoid forcing numbers like '5'
      continue;
    }
  }
  
  return formatted;
};

export const generateEmailVerificationCode = (): string => {
  return Math.random().toString(36).substring(2, 8).toUpperCase();
};

export const validateEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};
