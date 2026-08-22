import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider, signInWithPopup, signInWithEmailAndPassword, createUserWithEmailAndPassword } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyBanZa0ac_lscokn3WO3mQId3UchvvmJlg",
  authDomain: "razor-6943c.firebaseapp.com",
  projectId: "razor-6943c",
  storageBucket: "razor-6943c.firebasestorage.app",
  messagingSenderId: "716458692531",
  appId: "1:716458692531:web:e1d79885da23424862c5c6"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
