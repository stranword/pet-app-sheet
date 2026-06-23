/**
 * Google OAuth2 for write access to Sheets.
 * Uses expo-auth-session with Google provider.
 *
 * For production: replace CLIENT_ID with your Google Cloud OAuth client ID
 * (Web client for Expo Go / web, Android client for Android builds).
 */

import * as AuthSession from 'expo-auth-session';
import * as WebBrowser from 'expo-web-browser';
import { Platform } from 'react-native';

WebBrowser.maybeCompleteAuthSession();

const CLIENT_ID = process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID ?? '';

const discovery = {
  authorizationEndpoint: 'https://accounts.google.com/o/oauth2/v2/auth',
  tokenEndpoint: 'https://oauth2.googleapis.com/token',
};

const SCOPES = ['https://www.googleapis.com/auth/spreadsheets'];

export function useGoogleAuth() {
  const redirectUri = AuthSession.makeRedirectUri({
    scheme: 'sborka-app',
    useProxy: Platform.OS !== 'web',
  });

  const [request, response, promptAsync] = AuthSession.useAuthRequest(
    {
      clientId: CLIENT_ID,
      scopes: SCOPES,
      redirectUri,
      responseType: AuthSession.ResponseType.Token,
    },
    discovery,
  );

  const accessToken =
    response?.type === 'success' ? response.params.access_token : null;

  return { request, accessToken, promptAsync };
}
