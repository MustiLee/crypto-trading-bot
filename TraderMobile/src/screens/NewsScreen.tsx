import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  Linking,
  Image,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useNavigation } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList } from '../types';
import { useAuth } from '../context/AuthContext';

type NewsNavigationProp = StackNavigationProp<RootStackParamList, 'News'>;

interface NewsArticle {
  id: string;
  title: string;
  summary: string;
  source: string;
  publishedAt: string;
  url: string;
  imageUrl?: string;
  category: 'bitcoin' | 'ethereum' | 'altcoins' | 'defi' | 'nft' | 'market' | 'regulation';
}

const NewsScreen: React.FC = () => {
  const navigation = useNavigation<NewsNavigationProp>();
  const { user } = useAuth();
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  const mockNews: NewsArticle[] = [
    {
      id: '1',
      title: 'Bitcoin Reaches New All-Time High Above $110,000',
      summary: 'Bitcoin continues its bullish momentum, breaking through the $110,000 barrier amid increased institutional adoption and ETF inflows.',
      source: 'CoinDesk',
      publishedAt: '2025-01-09T14:30:00Z',
      url: 'https://coindesk.com',
      category: 'bitcoin',
    },
    {
      id: '2', 
      title: 'Ethereum 2.0 Staking Rewards Hit Record Levels',
      summary: 'Ethereum staking rewards reach unprecedented levels as network activity surges following the latest protocol upgrades.',
      source: 'CryptoNews',
      publishedAt: '2025-01-09T12:15:00Z',
      url: 'https://cryptonews.com',
      category: 'ethereum',
    },
    {
      id: '3',
      title: 'Major Altcoins Rally as Market Cap Exceeds $4 Trillion',
      summary: 'Alternative cryptocurrencies surge across the board, with SOL, ADA, and DOT leading gains as total market cap hits new highs.',
      source: 'Decrypt',
      publishedAt: '2025-01-09T10:45:00Z',
      url: 'https://decrypt.co',
      category: 'altcoins',
    },
    {
      id: '4',
      title: 'DeFi TVL Surpasses $300 Billion Milestone',
      summary: 'Decentralized Finance protocols see massive growth as Total Value Locked reaches a new milestone of $300 billion.',
      source: 'DeFi Pulse',
      publishedAt: '2025-01-09T09:20:00Z',
      url: 'https://defipulse.com',
      category: 'defi',
    },
    {
      id: '5',
      title: 'NFT Market Shows Signs of Recovery with 40% Growth',
      summary: 'The NFT marketplace experiences renewed interest with trading volumes up 40% this month, signaling potential market recovery.',
      source: 'NFT Now',
      publishedAt: '2025-01-09T08:00:00Z',
      url: 'https://nftnow.com',
      category: 'nft',
    },
    {
      id: '6',
      title: 'US SEC Approves More Crypto ETFs for Retail Investors',
      summary: 'The Securities and Exchange Commission greenlights additional cryptocurrency ETFs, expanding retail investor access to digital assets.',
      source: 'Bloomberg Crypto',
      publishedAt: '2025-01-08T16:30:00Z',
      url: 'https://bloomberg.com',
      category: 'regulation',
    },
  ];

  const categories = [
    { key: 'all', label: 'Tümü', emoji: '📰' },
    { key: 'bitcoin', label: 'Bitcoin', emoji: '₿' },
    { key: 'ethereum', label: 'Ethereum', emoji: '⟠' },
    { key: 'altcoins', label: 'Altcoinler', emoji: '🪙' },
    { key: 'defi', label: 'DeFi', emoji: '🏦' },
    { key: 'nft', label: 'NFT', emoji: '🎨' },
    { key: 'regulation', label: 'Düzenleme', emoji: '⚖️' },
  ];

  useEffect(() => {
    loadNews();
  }, []);

  const loadNews = () => {
    // Simulate API call delay
    setTimeout(() => {
      setArticles(mockNews);
    }, 500);
  };

  const onRefresh = async () => {
    setIsRefreshing(true);
    await new Promise(resolve => setTimeout(resolve, 1000));
    loadNews();
    setIsRefreshing(false);
  };

  const handleArticlePress = async (url: string) => {
    try {
      await Linking.openURL(url);
    } catch (error) {
      console.error('Error opening article:', error);
    }
  };

  const formatTime = (dateString: string) => {
    const now = new Date();
    const published = new Date(dateString);
    const diffInHours = Math.floor((now.getTime() - published.getTime()) / (1000 * 60 * 60));
    
    if (diffInHours < 1) return 'Şimdi';
    if (diffInHours < 24) return `${diffInHours} saat önce`;
    const diffInDays = Math.floor(diffInHours / 24);
    return `${diffInDays} gün önce`;
  };

  const getCategoryColor = (category: string) => {
    const colors = {
      bitcoin: '#f7931a',
      ethereum: '#627eea',
      altcoins: '#50c878',
      defi: '#ff6b6b',
      nft: '#9c88ff',
      market: '#4ecdc4',
      regulation: '#ffd93d',
    };
    return colors[category as keyof typeof colors] || '#667eea';
  };

  const filteredArticles = selectedCategory === 'all' 
    ? articles 
    : articles.filter(article => article.category === selectedCategory);

  const renderArticle = (article: NewsArticle) => (
    <TouchableOpacity
      key={article.id}
      style={styles.articleCard}
      onPress={() => handleArticlePress(article.url)}
      activeOpacity={0.7}
    >
      <View style={styles.articleHeader}>
        <View style={[
          styles.categoryBadge, 
          { backgroundColor: getCategoryColor(article.category) }
        ]}>
          <Text style={styles.categoryText}>
            {categories.find(cat => cat.key === article.category)?.emoji} 
            {' '}
            {article.category.toUpperCase()}
          </Text>
        </View>
        <Text style={styles.timeText}>{formatTime(article.publishedAt)}</Text>
      </View>
      
      <Text style={styles.articleTitle}>{article.title}</Text>
      <Text style={styles.articleSummary}>{article.summary}</Text>
      
      <View style={styles.articleFooter}>
        <Text style={styles.sourceText}>📰 {article.source}</Text>
        <Text style={styles.readMoreText}>Devamını oku →</Text>
      </View>
    </TouchableOpacity>
  );

  return (
    <LinearGradient
      colors={['#667eea', '#764ba2']}
      style={styles.container}
    >
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>📰 Kripto Haberler</Text>
          <Text style={styles.subtitle}>Son gelişmeler ve analiz</Text>
        </View>
        
        <View style={styles.userSection}>
          {user ? (
            <TouchableOpacity 
              style={styles.profileButton}
              onPress={() => navigation.navigate('MainTabs', { screen: 'Profile' })}
            >
              <Text style={styles.profileButtonText}>👤 {user.first_name}</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity 
              style={styles.loginButton}
              onPress={() => navigation.navigate('AuthStack', { screen: 'Login', params: { returnTo: 'News' } })}
            >
              <Text style={styles.loginButtonText}>👤 Giriş</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      {/* Category Filter */}
      <ScrollView 
        horizontal 
        showsHorizontalScrollIndicator={false}
        style={styles.categoriesContainer}
        contentContainerStyle={styles.categoriesContent}
      >
        {categories.map((category) => (
          <TouchableOpacity
            key={category.key}
            style={[
              styles.categoryButton,
              selectedCategory === category.key && styles.categoryButtonActive
            ]}
            onPress={() => setSelectedCategory(category.key)}
          >
            <Text style={[
              styles.categoryButtonText,
              selectedCategory === category.key && styles.categoryButtonTextActive
            ]}>
              {category.emoji} {category.label}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* News Articles */}
      <ScrollView
        style={styles.scrollView}
        refreshControl={
          <RefreshControl 
            refreshing={isRefreshing} 
            onRefresh={onRefresh}
            tintColor="white"
          />
        }
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.articlesContainer}>
          {filteredArticles.map(renderArticle)}
        </View>
      </ScrollView>

    </LinearGradient>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: 'white',
  },
  subtitle: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
    marginTop: 4,
  },
  categoriesContainer: {
    maxHeight: 50,
    marginBottom: 10,
  },
  categoriesContent: {
    paddingHorizontal: 20,
    paddingVertical: 5,
  },
  categoryButton: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    marginRight: 10,
  },
  categoryButtonActive: {
    backgroundColor: 'rgba(255,255,255,0.9)',
  },
  categoryButtonText: {
    color: 'white',
    fontSize: 12,
    fontWeight: '600',
  },
  categoryButtonTextActive: {
    color: '#667eea',
  },
  scrollView: {
    flex: 1,
    paddingHorizontal: 20,
  },
  articlesContainer: {
    paddingBottom: 20,
  },
  articleCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderRadius: 15,
    padding: 20,
    marginBottom: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 5,
  },
  articleHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  categoryBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  categoryText: {
    color: 'white',
    fontSize: 10,
    fontWeight: '700',
  },
  timeText: {
    fontSize: 12,
    color: '#666',
  },
  articleTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#333',
    marginBottom: 8,
    lineHeight: 24,
  },
  articleSummary: {
    fontSize: 14,
    color: '#555',
    lineHeight: 20,
    marginBottom: 12,
  },
  articleFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: '#eee',
    paddingTop: 12,
  },
  sourceText: {
    fontSize: 12,
    color: '#888',
    fontWeight: '500',
  },
  readMoreText: {
    fontSize: 12,
    color: '#667eea',
    fontWeight: '600',
  },
  userSection: {
    alignItems: 'flex-end',
  },
  loginButton: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 15,
  },
  loginButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
  },
  profileButton: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 15,
  },
  profileButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
  },
});

export default NewsScreen;