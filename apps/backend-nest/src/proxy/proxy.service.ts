import { Injectable, HttpException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

interface UploadedPdf {
  buffer: Buffer;
  originalname: string;
  mimetype: string;
}

@Injectable()
export class ProxyService {
  private readonly fapiUrl: string;

  constructor(private readonly configService: ConfigService) {
    this.fapiUrl = this.configService.get<string>(
      'FASTAPI_URL',
      'http://localhost:8000',
    );
  }

  get<T>(path: string): Promise<T> {
    return this.request<T>('GET', path);
  }

  post<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>('POST', path, body);
  }

  delete<T>(path: string): Promise<T> {
    return this.request<T>('DELETE', path);
  }

  async uploadFile<T>(file: UploadedPdf, uploadedBy: string): Promise<T> {
    const form = new FormData();
    form.append(
      'file',
      new Blob([new Uint8Array(file.buffer)], { type: file.mimetype }),
      file.originalname,
    );
    form.append('uploaded_by', uploadedBy);

    const res = await fetch(`${this.fapiUrl}/documents/upload`, {
      method: 'POST',
      body: form,
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new HttpException(data, res.status);
    return data as T;
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    const res = await fetch(`${this.fapiUrl}${path}`, {
      method,
      headers:
        body !== undefined ? { 'Content-Type': 'application/json' } : {},
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new HttpException(data, res.status);
    return data as T;
  }
}
