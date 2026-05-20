import { useState, useCallback } from "react";
import { fetchVapidPublicKey, subscribePush, unsubscribePush } from "../review-api";

export function usePushSubscription() {
  const [permissionState, setPermissionState] = useState<PermissionState | "default">(
    "Notification" in window ? Notification.permission as PermissionState : "default"
  );
  const [loading, setLoading] = useState(false);

  const subscribe = useCallback(async () => {
    if (!("PushManager" in window)) return;
    setLoading(true);
    try {
      const permission = await Notification.requestPermission();
      setPermissionState(permission as PermissionState);
      if (permission !== "granted") return;

      const publicKey = await fetchVapidPublicKey();
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: publicKey,
      });

      await subscribePush(subscription.toJSON());
    } catch {
    } finally {
      setLoading(false);
    }
  }, []);

  const unsubscribe = useCallback(async () => {
    setLoading(true);
    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();
      if (subscription) {
        await subscription.unsubscribe();
      }
      await unsubscribePush();
    } catch {
    } finally {
      setLoading(false);
    }
  }, []);

  return { permissionState, loading, subscribe, unsubscribe };
}
