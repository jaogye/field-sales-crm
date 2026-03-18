// Stats are available on the owner's Streamlit dashboard.
import { Redirect } from 'expo-router';
export default function StatsRedirect() {
  return <Redirect href="/(tabs)" />;
}
