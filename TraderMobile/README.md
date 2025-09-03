# Trader Mobile - React Native App

React Native mobil uygulaması ile kripto para trading dashboard'u ve strateji test sistemi.

## Özellikler

- 👤 **Kullanıcı Yönetimi**: Login/Register sistemi
- 📊 **Dashboard**: Real-time kripto para verileri (BTC, ETH, XRP, BNB, ADA, SOL, DOT, POL, AVAX, LINK)
- 🎯 **Strateji Test**: Her kripto varlık için özel strateji oluşturma ve test etme
- 📈 **Teknik İndikatörler**: RSI, MACD, Bollinger Bands
- 💹 **Backtest**: Strateji performans analizi
- 🔄 **Real-time WebSocket**: Canlı veri akışı

## Teknolojiler

- **React Native** - Expo framework
- **TypeScript** - Type safety
- **React Navigation** - Sayfa geçişleri
- **AsyncStorage** - Yerel veri saklama
- **Linear Gradient** - UI tasarımı
- **WebSocket** - Real-time bağlantı

## Kurulum

1. Projeyi klonlayın:
\`\`\`bash
cd TraderMobile
\`\`\`

2. Bağımlılıkları yükleyin:
\`\`\`bash
npm install
\`\`\`

3. Backend sunucusunu başlatın:
\`\`\`bash
cd ../deployment
docker-compose up
\`\`\`

4. Mobil uygulamayı başlatın:
\`\`\`bash
npm run web     # Web tarayıcısında
npm run ios     # iOS simulator
npm run android # Android emulator
\`\`\`

## API Yapılandırması

\`src/services/api.ts\` dosyasındaki \`API_BASE_URL\` değerini backend sunucunuza göre ayarlayın:

\`\`\`typescript
const API_BASE_URL = 'http://localhost:8000'; // Backend URL
\`\`\`

## Proje Yapısı

\`\`\`
TraderMobile/
├── src/
│   ├── components/          # Reusable components
│   ├── context/            # React Context (Auth)
│   ├── navigation/         # Navigation setup
│   ├── screens/           # App screens
│   │   ├── LoginScreen.tsx
│   │   ├── RegisterScreen.tsx
│   │   ├── DashboardScreen.tsx
│   │   └── StrategyTestScreen.tsx
│   ├── services/          # API services
│   └── types/             # TypeScript types
├── App.tsx               # Main app component
└── package.json
\`\`\`

## Ekranlar

### 1. Login/Register
- Kullanıcı girişi ve kayıt olma
- Email doğrulama sistemi
- Session yönetimi

### 2. Dashboard
- 10 kripto para canlı takibi
- Real-time fiyat ve sinyal güncellemeleri
- Her varlık için strateji test butonu
- Kullanıcı profil bilgileri (sağ üst köşe)

### 3. Strateji Test
- Kripto varlık bazında strateji oluşturma
- Teknik indikatör parametreleri ayarlama
- Risk yönetimi ayarları
- Backtest sonuçları görüntüleme
- Strateji kaydetme ve aktifleştirme

## API Endpoints

Backend ile iletişim için kullanılan API endpoints:

- \`POST /api/v1/auth/login\` - Kullanıcı girişi
- \`POST /api/v1/auth/register\` - Kullanıcı kaydı
- \`POST /api/v1/auth/logout\` - Çıkış
- \`GET /api/v1/auth/me\` - Kullanıcı bilgileri
- \`POST /api/v1/strategies/create\` - Strateji oluşturma
- \`POST /api/v1/strategies/{id}/test\` - Strateji testi
- \`GET /api/v1/strategies/my-strategies\` - Kullanıcı stratejileri
- \`POST /api/v1/strategies/{id}/activate\` - Strateji aktifleştirme
- \`GET /api/v1/dashboard/symbols\` - Dashboard verileri
- \`WS /ws\` - WebSocket real-time data

## Backend Entegrasyonu

Bu mobil uygulama, mevcut Python FastAPI backend'i ile entegre çalışmak üzere tasarlanmıştır:

1. Backend sunucusu \`http://localhost:8000\` adresinde çalışmalıdır
2. WebSocket endpoint'i \`ws://localhost:8000/ws\` üzerinden real-time data sağlar
3. API endpoints \`/api/v1\` prefix'i ile organize edilmiştir

## Geliştirme Notları

- Real-time WebSocket bağlantısı otomatik yeniden bağlanma özelliğine sahiptir
- Kullanıcı oturumu AsyncStorage'da saklanır
- Tüm API çağrıları hata yönetimi ile korunmuştur
- UI/UX tasarımı iOS ve Android için optimize edilmiştir

## Yakın Özellikleri

- 📱 Push notifications
- 📊 Advanced charting
- 🔔 Price alerts
- 💼 Portfolio management