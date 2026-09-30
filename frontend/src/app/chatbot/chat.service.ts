import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ChatMessage, ChatProfile, ChatResponse } from './chat.models';

const PROFILE_KEY = 'ctdata-chat-profile';

@Injectable({ providedIn: 'root' })
export class ChatService {
  private readonly http = inject(HttpClient);

  ask(message: string, profile: ChatProfile, history: ChatMessage[]): Observable<ChatResponse> {
    return this.http.post<ChatResponse>('/api/chat', {
      message,
      profile,
      history: history.map(({ role, content }) => ({ role, content })),
    });
  }

  loadProfile(): ChatProfile | null {
    try {
      const raw = localStorage.getItem(PROFILE_KEY);
      return raw ? (JSON.parse(raw) as ChatProfile) : null;
    } catch {
      return null;
    }
  }

  saveProfile(profile: ChatProfile | null): void {
    try {
      if (profile) localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
      else localStorage.removeItem(PROFILE_KEY);
    } catch {
      /* storage unavailable (private mode) - profile just won't persist */
    }
  }
}
