import {
  Injectable, NestInterceptor, ExecutionContext, CallHandler, Logger,
} from '@nestjs/common';
import { Observable, tap, catchError, throwError } from 'rxjs';

@Injectable()
export class LoggingInterceptor implements NestInterceptor {
  private readonly logger = new Logger('HTTP');

  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    const req = context.switchToHttp().getRequest();
    const { method, url } = req;
    const userId = req.user?.id ?? '-';
    const start = Date.now();

    return next.handle().pipe(
      tap(() => {
        const ms = Date.now() - start;
        const status = context.switchToHttp().getResponse().statusCode;
        this.logger.log(`${method} ${url} ${status} ${ms}ms [user:${userId}]`);
      }),
      catchError((err) => {
        const ms = Date.now() - start;
        this.logger.warn(`${method} ${url} ERROR ${ms}ms [user:${userId}] — ${err.message}`);
        return throwError(() => err);
      }),
    );
  }
}
