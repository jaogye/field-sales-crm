/**
 * Contact Sync Service — reads phone contacts and syncs to CRM backend.
 */
import * as Contacts from 'expo-contacts';
import api from './api';

export async function requestContactPermission() {
  const { status } = await Contacts.requestPermissionsAsync();
  return status === 'granted';
}

export async function getPhoneContacts() {
  const { data } = await Contacts.getContactsAsync({
    fields: [
      Contacts.Fields.Name,
      Contacts.Fields.FirstName,
      Contacts.Fields.LastName,
      Contacts.Fields.PhoneNumbers,
    ],
    sort: Contacts.SortTypes.FirstName,
  });

  // Filter contacts that have at least one phone number
  return data.filter(c => c.phoneNumbers && c.phoneNumbers.length > 0);
}

export async function syncContactsToBackend() {
  const hasPermission = await requestContactPermission();
  if (!hasPermission) {
    throw new Error('Contact permission denied');
  }

  const contacts = await getPhoneContacts();
  const result = await api.syncContactos(contacts);

  return {
    totalOnPhone: contacts.length,
    created: result.created,
    skipped: result.skipped,
  };
}
