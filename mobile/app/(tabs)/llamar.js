// Call logging is now integrated in the Clientes screen (index.js).
import { Redirect } from 'expo-router';
export default function LlamarRedirect() {
  return <Redirect href="/(tabs)" />;
}
